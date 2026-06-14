# Scaling, Validation, and Operational Considerations

> **Prerequisite:** Read [`00-feasibility-overview.md`](./00-feasibility-overview.md) and [`01-proposed-pipeline.md`](./01-proposed-pipeline.md).

---

## 1. Performance Budget

### 1.1 Measured Performance (2026-06-14, this machine)

| Operation | Time | Throughput |
|---|---|---|
| `search_fuzzy` cold start | 2.3s | — (one-time per version) |
| `search_fuzzy` warm | 0.18–0.19s/query | ~5.3 queries/sec |
| GeoPandas `read_file` ADM4 | ~8s | 42,048 features |
| GeoPandas `simplify(0.005)` ADM4 | ~15s | Full barangay layer |
| GeoJSON write ADM4 (tol=0.005) | ~3s | ~150 MB |

### 1.2 Estimated Full Pipeline Time

| Phase | Est. Time | Dominant Cost |
|---|---|---|
| Phase 1: Convert (all ADM) | ~30s | simplify() on 42K polygons |
| Phase 2: Classify ADM0–ADM2 | <1s | PCODE dict lookups |
| Phase 2: Classify ADM3 (1,642) | ~30s | ~160 search_fuzzy fallback calls |
| Phase 2+3: Classify+Enrich ADM4 (42,048) | ~15–20 min | ~4,000–6,000 search_fuzzy fallback calls |
| Phase 4: Split & Write | ~5s | JSON serialization |

**Total estimated: ~16–21 minutes** for a full pipeline run from scratch.

If Phase 1 outputs already exist (`--skip-convert`): **~16–20 minutes**, dominated by ADM4 enrichment fallback.

### 1.3 Can We Parallelize?

The `search_fuzzy` calls in Phase 2/3 are **independent** — each feature is classified in isolation. They can be parallelized with `concurrent.futures.ThreadPoolExecutor`:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=8) as pool:
    futures = {
        pool.submit(classify_one, feature): feature
        for feature in unmatched_features
    }
    for future in as_completed(futures):
        result = future.result()
        # ...merge back
```

**Caveat:** The `barangay` package uses a singleton `Database` with in-memory caches. Thread safety is **not guaranteed** — concurrent reads might be safe (read-only parquet), but this needs testing. If unsafe, use `ProcessPoolExecutor` instead (higher overhead but no shared state).

**With 8 parallel workers:** ADM4 fallback drops from ~20 min to ~3 min. Total pipeline: **~5–6 minutes**.

---

## 2. Validation Strategy

### 2.1 Feature Count Reconciliation

After splitting, verify counts match PSGC:

```python
expected_counts = {
    "regions": len(bg.regions.to_frame()),                      # 18
    "provinces": len(bg.provinces.to_frame()),                  # 82
    "municipalities": len(bg.municipalities.to_frame()),        # ~1,493
    "highly_urbanized_cities": len(bg.hucs.to_frame()),         # 33
    "independent_component_cities": len(bg.iccs.to_frame()),    # 6
    "component_cities": len(bg.component_cities.to_frame()),    # ~111
    "submunicipalities": len(bg.submunicipalities.to_frame()),  # 14
    "special_geographic_areas": len(bg.special_geographic_areas.to_frame()),  # 1
    "barangays": len(bg.barangays.to_frame()),                  # ~42,010
}
```

**Tolerances:**
- `regions`, `provinces`, `hucs`, `iccs`, `component_cities`, `submunicipalities`, `sga`: **exact match required**
- `municipalities`: ±2 (NAMRIA may have slight version lag)
- `barangays`: ±50 (NAMRIA includes non-admin areas; PSGC version differences)

### 2.2 PCODE Coverage Audit

For each output file, generate a coverage report:

```
highly_urbanized_cities.geojson:
  Features:          33
  PSGC expected:     33
  Exact pcode match: 30 (90.9%)
  HUC map match:      3 (9.1%)
  Fuzzy match:        0
  Unresolved:         0
  Missing from PSGC:  0
  Extra vs PSGC:      0
```

This reuses the existing `coverage.py` infrastructure — extend `compute_coverage_with_huc` to work per-entity-type instead of per-ADM-level.

### 2.3 Geometric Integrity

Verify no polygons are corrupted during split:

```python
for output_file in hierarchical_dir.glob("*.geojson"):
    gdf = gpd.read_file(output_file)
    assert gdf.geometry.is_valid.all(), f"{output_file} has invalid geometries"
    assert len(gdf) > 0, f"{output_file} is empty"
```

### 2.4 Round-Trip Test

Load each output file → verify every feature has:
- `psgc_id` (non-null)
- `psgc_type` (matches filename)
- `match_method` (one of: exact, huc_map, fuzzy, fallback)
- At least one hierarchy field populated (region or province or municipality)

---

## 3. Data Version Alignment

### 3.1 The NAMRIA Snapshot Problem

NAMRIA shapefiles are versioned `2023-11-06`. PSGC snapshots span `2021-08-19` through `2026-04-13`. There's an inherent temporal mismatch:

- NAMRIA reflects boundaries as of late 2023
- PSGC reflects administrative codes as of the snapshot date

**Impact:** Some entities may exist in PSGC but not NAMRIA (newly created barangays) or vice versa (renamed/recoded entities).

### 3.2 Recommended Pairing

| NAMRIA Version | Best PSGC Match | Rationale |
|---|---|---|
| 2023-11-06 | `2023-10-24` | Closest temporal match |

The pipeline should default to this pairing but allow override via `--psgc-date`.

### 3.3 Handling Temporal Mismatches

Features in NAMRIA that don't exist in the PSGC snapshot:
- Mark as `psgc_status="temporal_mismatch"`
- Keep in output file with original NAMRIA attributes
- Log to `classification_report.json`

Features in PSGC not found in NAMRIA:
- These are **missing polygons**, not classification failures
- Log to `missing_geometries.json` for tracking

---

## 4. Output File Specifications

### 4.1 GeoJSON Schema

Each Feature's properties follow this schema:

```typescript
interface FeatureProperties {
  // Original NAMRIA attributes (preserved)
  ADM1_EN: string;
  ADM1_PCODE: string;
  ADM2_EN: string;
  ADM2_PCODE: string;
  ADM3_EN: string;
  ADM3_PCODE: string;
  ADM4_EN: string;
  ADM4_PCODE: string;

  // PSGC enrichment
  psgc_id: string;              // 10-digit PSGC code
  psgc_pcode: string;           // "PH" + prefix
  psgc_name: string;            // Official PSGC name
  psgc_type: string;            // AdminLevel value
  psgc_status: string;          // matched | fuzzy | unresolved | temporal_mismatch
  match_method: string;         // exact | huc_map | fuzzy | fallback
  match_confidence: number;     // 0.0–1.0

  // Resolved hierarchy (from EnrichedRecord)
  region?: string;
  province?: string;
  highly_urbanized_city?: string;
  municipality?: string;
  component_city?: string;
  independent_component_city?: string;
  submunicipality?: string;

  // Traceability
  namria_adm2_pcode?: string;   // Original parent (for re-nested HUCs/ICCs)
  sga_member?: boolean;         // True for SGA barangays
}
```

### 4.2 Coordinate Reference System

NAMRIA shapefiles use **EPSG:4326** (WGS84). GeoJSON outputs should preserve this. All coordinates are latitude/longitude in decimal degrees.

### 4.3 File Size Management

| Output File | Est. Size | Notes |
|---|---|---|
| `barangays.geojson` | ~150 MB | Dominant — consider per-region splitting |
| `municipalities.geojson` | ~30 MB | |
| `provinces.geojson` | ~15 MB | |
| `hucs.geojson` | ~10 MB | |
| `component_cities.geojson` | ~10 MB | |
| All others | <5 MB each | |

**For `barangays.geojson` at 150 MB:** Consider an optional `--split-regions` flag that writes `barangays_region_01.geojson`, `barangays_region_02.geojson`, etc. This keeps individual files under 20 MB for web serving.

---

## 5. Operational Considerations

### 5.1 Re-runnability

The pipeline must be **idempotent** — running it twice produces identical output. Ensure:
- `bg.use_version(date)` is called at the start to pin PSGC data
- Fuzzy match scores are deterministic (rapidfuzz is deterministic)
- Output files are overwritten, not appended

### 5.2 Caching

The `barangay` package caches:
- PSGC data versions (parquet files) — persists across runs
- Fuzzer base — in-memory only, lost on restart

The pipeline caches:
- HUC mapping (`huc_adm2_mapping.json`) — persists, regenerated if missing
- Enriched GeoJSON — in `{date}/enriched_t0p005/`

**Recommendation:** Add a `--cache-dir` option for PSGC data to avoid re-downloading on each run.

### 5.3 Logging

Proposed log structure:

```
INFO  Phase 1: Converting 5 shapefiles (tolerance=0.005)
INFO    ADM0: 3,640 features → adm0.geojson (0.1 MB)
INFO    ADM4: 42,048 features → adm4.geojson (148.2 MB)
INFO  Phase 2: Classifying features
INFO    ADM2: 88 features → 82 provinces, 4 mm_districts, 1 sga, 1 huc_isabela
INFO    ADM3: 1,642 features
INFO      Exact pcode match: 1,488 (90.6%)
INFO      HUC map match: 94 (5.7%)
INFO      Fuzzy match: 55 (3.4%)
INFO      Unresolved: 5 (0.3%)
INFO    ADM4: 42,048 features (excluding 23 non-admin)
INFO      Exact + parent-scoped: 36,810 (87.6%)
INFO      Fuzzy fallback: 4,972 (11.8%)
INFO      Unresolved: 243 (0.6%)
INFO  Phase 4: Writing 9 output files
INFO    barangays.geojson: 42,025 features
INFO    municipalities.geojson: 1,493 features
INFO    ...
```

### 5.4 Manual Review Workflow

Unresolved features are written to `unresolved.geojson`. Proposed review process:

1. Open `unresolved.geojson` in a GIS tool
2. Compare NAMRIA name/location against PSGC records
3. Add manual mapping to `manual_overrides.json`:
   ```json
   {
     "PH0722202": {
       "psgc_id": "0722700000",
       "psgc_type": "highly_urbanized_city",
       "note": "City of Cebu — missed by fuzzy due to name variant"
     }
   }
   ```
4. Re-run pipeline — manual overrides take priority over all other methods

---

## 6. Limitations and Open Questions

### 6.1 What This Pipeline Cannot Do

1. **Create polygons for entities that don't exist in NAMRIA.** If PSGC has a barangay created after 2023-11-06, it won't have geometry.
2. **Fix topological errors in NAMRIA data.** Overlapping polygons, gaps, and slivers are preserved.
3. **Resolve historical boundaries.** The pipeline works on a single snapshot. Historical comparison requires running it on multiple dates.

### 6.2 Open Questions for Review

1. **Should HUCs retain their NAMRIA province nesting in a `province_geometric` field?** Some users may want to know which province geographically surrounds an HUC, even though PSGC doesn't record this.

2. **Should `barangays.geojson` include SGA barangays, or should they only be in `special_geographic_areas.geojson`?** See Edge Case #4 in [`02-edge-cases.md`](./02-edge-cases.md).

3. **Should submunicipalities be a separate output if NAMRIA doesn't have their polygons?** If they only exist as PSGC entities without NAMRIA geometry, `submunicipalities.geojson` would be empty. Alternative: generate approximate polygons from their constituent barangays.

4. **Tolerance strategy:** Should different entity types use different simplification tolerances? Provinces can tolerate 0.005° (500m) simplification, but barangay boundaries may need 0.001° (100m) for accuracy.

5. **Naming convention:** Should output files use `hucs.geojson` (short) or `highly_urbanized_cities.geojson` (descriptive)? Recommendation: descriptive, matching PSGC terminology.

---

## 7. Implementation Estimate

| Component | Effort | Files |
|---|---|---|
| `classifier.py` — classification cascade | 2–3 days | New |
| `splitter.py` — output file splitting | 0.5 day | New |
| Enhance `enrich.py` — add psgc_type, match_method | 1 day | Modify |
| CLI command `build-hierarchical` | 0.5 day | Modify `cli.py` |
| Validation & coverage per type | 1 day | Modify `coverage.py` |
| Tests | 2 days | New |
| Manual override mechanism | 0.5 day | New |

**Total: ~7–8 days** of focused implementation work.

---

## 8. Decision Matrix: Go/No-Go

| Criterion | Status | Weight |
|---|---|---|
| Technical feasibility | ✅ Confirmed | High |
| `search_fuzzy` supports needed levels | ✅ Confirmed (with match_hooks) | High |
| Existing code covers ~90% of cases | ✅ PCODE matching + HUC mapping | High |
| Edge cases have known resolutions | ✅ See [`02-edge-cases.md`](./02-edge-cases.md) | Medium |
| Performance acceptable (~20 min single, ~5 min parallel) | ✅ Feasible | Medium |
| Submunicipality polygon availability | ❓ Needs verification | Medium |
| `search_fuzzy` thread safety | ❓ Needs testing | Low (workaround exists) |

**Recommendation: GO.** Start with a prototype that handles ADM0–ADM3 (the classification-heavy layers), validate against known PSGC counts, then extend to ADM4 barangay splitting.
