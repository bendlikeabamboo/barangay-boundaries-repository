# Proposed Pipeline: PSGC-Hierarchical GeoJSON Generation

> **Prerequisite:** Read [`00-feasibility-overview.md`](./00-feasibility-overview.md) first.

---

## 1. High-Level Architecture

```
NAMRIA Shapefiles (namria/*.shp)
       │
       ▼
┌─────────────────────────┐
│  Phase 1: Convert       │  (existing namria_converter.py)
│  .shp → adm{0-4}.geojson│
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Phase 2: Classify      │  (NEW — the core of this proposal)
│  Assign PSGC type to    │
│  each feature via       │
│  PCODE + HUC map +      │
│  search_fuzzy           │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Phase 3: Enrich        │  (enhanced enrich.py)
│  Add psgc_id, psgc_code,│
│  psgc_name, psgc_type,  │
│  hierarchy fields,      │
│  match_confidence       │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Phase 4: Split & Write │  (NEW)
│  Write one .geojson per │
│  PSGC entity type       │
└─────────────────────────┘
```

---

## 2. Phase 1 — Convert (Existing, Unchanged)

Already implemented in `namria_converter.py:39`. Produces `adm{0-4}.geojson` with Douglas-Peucker simplification (tolerance=0.005°).

No changes needed. This phase is the input to Phase 2.

---

## 3. Phase 2 — Classify (New)

**Module:** `barangay_boundaries_repository/classifier.py` (proposed)

This is the heart of the new pipeline. For each feature in each ADM layer, determine its PSGC entity type.

### 3.1 Classification for ADM0 and ADM1

Trivial — 1:1 mapping:
- ADM0 → `country` (single feature, always Philippines)
- ADM1 → `region` (17 features, PCODE prefix match works perfectly)

```python
# ADM1: every feature is a region
for feature in adm1_data["features"]:
    feature["properties"]["psgc_type"] = "region"
```

### 3.2 Classification for ADM2

ADM2 contains 88 features of mixed types. The split:

| ADM2 Feature Type | Count | Detection Method |
|---|---|---|
| Province | ~82 | `ADM2_PCODE` matches `bg.provinces` pcode prefix |
| MM Legislative District | 4 | `ADM2_PCODE` starts with `PH13` but ≠ `PH13` |
| SGA virtual province | 1 | `ADM2_EN` contains "Special Geographic Area" |
| HUC-as-province (Isabela) | 1 | `ADM2_PCODE == "PH09097"` (special case) |

```python
def classify_adm2(props, provinces_pcodes, huc_mapping):
    pcode = props["ADM2_PCODE"]
    if pcode in provinces_pcodes:
        return "province"
    vp = huc_mapping.get("virtual_provinces", {}).get(pcode, {})
    return vp.get("type", "unknown")  # "mm_district", "sga", "huc_isabela"
```

**Output:** All non-province ADM2 features are **not** written to `provinces.geojson`. They are virtual groupings used only for re-nesting.

### 3.3 Classification for ADM3 — The Complex Case

ADM3 has 1,642 features spanning four PSGC types. Classification cascade:

```
Step 1: PCODE exact match
  Build lookup from bg.hucs, bg.iccs, bg.component_cities, bg.municipalities
  Match ADM3_PCODE → assign type from matched set

Step 2: HUC mapping
  Look up ADM3_PCODE in huc_mapping["namria_adm3_to_psgc"]
  → get PSGC pcode → lookup type from barangay package

Step 3: search_fuzzy classification (for ~10% unmatched)
  Run multi-pass:
    Pass A: city types (HUC → ICC → CC), threshold=85
    Pass B: municipality, threshold=80
  Accept highest scorer

Step 4: Unresolved → mark for manual review
```

**Detailed search_fuzzy classification:**

```python
def classify_by_fuzzy(name: str, adm2_name: str) -> tuple[str | None, float]:
    """Try each city type, then municipality. Return (psgc_type, score)."""
    from barangay.search import search_fuzzy
    from barangay.models import AdminLevel

    candidates = [
        (AdminLevel.HIGHLY_URBANIZED_CITY, ["highly_urbanized_city"], 85),
        (AdminLevel.INDEPENDENT_COMPONENT_CITY, ["independent_component_city"], 85),
        (AdminLevel.COMPONENT_CITY, ["component_city"], 85),
        (AdminLevel.MUNICIPALITY, ["province", "municipality"], 80),
    ]

    best_type = None
    best_score = 0.0

    for level, hooks, threshold in candidates:
        results = search_fuzzy(name, level=level, match_hooks=hooks,
                               threshold=threshold, limit=1)
        if results and results[0].score > best_score:
            best_score = results[0].score
            best_type = level.value

    return best_type, best_score
```

**Why this ordering matters:** Cities are rarer and more distinctive. A score of 85+ against 33 HUCs is more reliable than 85+ against 1,493 municipalities. We try the most specific (and smallest search space) first.

### 3.4 Classification for ADM4

ADM4 has 42,048 features. Classification into `barangay` vs `submunicipality` vs `non-administrative`:

```
Step 1: Non-administrative filter
  Check _NON_ADMIN_PATTERNS (forest land, cemetery, etc.)
  → exclude these entirely

Step 2: PCODE + parent-scoped match (existing enrich.py logic)
  Use ADM3_PCODE → resolved PSGC parent → child barangay dict
  Match ADM4_PCODE or fuzzy name within parent scope

Step 3: search_fuzzy fallback (existing _fallback_search_batch)
  Multi-pass: [barangay, municipality, province] → [barangay, municipality] → [barangay]

Step 4: Determine if parent is a submunicipality
  If the matched barangay's parent is AdminLevel.SUBMUNICIPALITY
  → classify as "submunicipality" (these are actually submuni barangays)
```

**Important distinction:** Submunicipalities in PSGC are themselves LGUs (14 total, all under Manila/Quezon City HUCs). Their barangays are barangays. The `submunicipalities.geojson` output should contain the **14 submunicipality LGU polygons**, not their barangays. These need to be extracted from ADM4 by matching against `bg.submunicipalities` pcodes.

---

## 4. Phase 3 — Enrich (Enhanced)

Extends the existing `enrich.py` with:

### 4.1 Additional Properties

Each feature gets:
- `psgc_type` — from Phase 2 classification (e.g. `"highly_urbanized_city"`)
- `psgc_id` — 10-digit PSGC code
- `psgc_pcode` — `"PH" + psgc_id[:n]` (NAMRIA-style pcode)
- `psgc_name` — official PSGC name
- `match_method` — `"exact"`, `"huc_map"`, `"fuzzy"`, `"fallback"`
- `match_confidence` — 0.0–1.0
- Hierarchy fields (from `EnrichedRecord.to_dict()`): `region`, `province`, `municipality`, etc.

### 4.2 Hierarchy Re-nesting

For HUCs and ICCs that NAMRIA nests under a province:

1. Read the polygon geometry from ADM3
2. Re-assign the `ADM2_PCODE` to the **region** pcode (from PSGC parent)
3. Clear the province-level hierarchy (since PSGC says HUC → region, not HUC → province)
4. Preserve the original NAMRIA hierarchy in `namria_adm2_pcode` for traceability

```python
# Example: City of Baguio
# NAMRIA: ADM3_PCODE=PH0128503 (under Benguet PH01285)
# PSGC:   psgc_id=1430300000 (under CAR region PH14)
feature["properties"]["namria_adm2_pcode"] = "PH01285"  # original
feature["properties"]["psgc_parent_pcode"] = "PH14"     # re-nested
feature["properties"]["province"] = None                 # cleared
feature["properties"]["region"] = "Cordillera Administrative Region (CAR)"
```

---

## 5. Phase 4 — Split & Write (New)

**Module:** `barangay_boundaries_repository/splitter.py` (proposed)

### 5.1 Output Structure

```
{date}/hierarchical/
├── regions.geojson
├── provinces.geojson
├── municipalities.geojson
├── highly_urbanized_cities.geojson
├── independent_component_cities.geojson
├── component_cities.geojson
├── submunicipalities.geojson
├── barangays.geojson
├── special_geographic_areas.geojson
├── unresolved.geojson          ← features that couldn't be classified
└── classification_report.json  ← summary of match methods + confidence
```

### 5.2 Split Logic

```python
OUTPUT_MAP = {
    "country":                    "country",            # ADM0 (single feature)
    "region":                     "regions",            # ADM1
    "province":                   "provinces",          # ADM2 subset
    "municipality":               "municipalities",     # ADM3 subset
    "highly_urbanized_city":      "highly_urbanized_cities",
    "independent_component_city": "independent_component_cities",
    "component_city":             "component_cities",
    "submunicipality":            "submunicipalities",
    "barangay":                   "barangays",
    "special_geographic_area":    "special_geographic_areas",
}

def split_by_type(enriched_features: list[dict], output_dir: Path):
    buckets = defaultdict(list)
    for feature in enriched_features:
        psgc_type = feature["properties"].get("psgc_type", "unresolved")
        filename = OUTPUT_MAP.get(psgc_type, "unresolved")
        buckets[filename].append(feature)

    for filename, features in buckets.items():
        write_geojson(output_dir / f"{filename}.geojson", features)
```

### 5.3 FeatureCollection Metadata

Each output file's GeoJSON should include a `metadata` field:

```json
{
  "type": "FeatureCollection",
  "metadata": {
    "psgc_type": "highly_urbanized_city",
    "psgc_version": "2026-04-13",
    "namria_version": "2023-11-06",
    "feature_count": 33,
    "match_summary": {
      "exact": 30,
      "huc_map": 3,
      "fuzzy": 0,
      "unresolved": 0
    }
  },
  "features": [...]
}
```

---

## 6. CLI Integration

Proposed new CLI command:

```
brgybnd build-hierarchical --date YYYY-MM-DD [--tolerance 0.005] [--skip-convert]
```

This orchestrates Phases 1–4 and outputs to `{date}/hierarchical/`.

### Suggested implementation in `cli.py`:

```python
@cli.command("build-hierarchical")
@click.option("--date", required=True)
@click.option("--tolerance", default=0.005, type=float)
@click.option("--skip-convert", is_flag=True, help="Reuse existing adm{0-4}.geojson")
def build_hierarchical(date, tolerance, skip_convert):
    """Build PSGC-hierarchy-organized GeoJSON from NAMRIA shapefiles."""
    from barangay_boundaries_repository.geojson_pipeline import run_geojson_pipeline
    from barangay_boundaries_repository.classifier import classify_all
    from barangay_boundaries_repository.splitter import split_by_type

    # Phase 1: Convert (or reuse)
    if not skip_convert:
        run_geojson_pipeline(date, tolerance=tolerance)

    # Phase 2+3: Classify + Enrich
    enriched = classify_all(date)

    # Phase 4: Split
    output_dir = Path(date) / "hierarchical"
    split_by_type(enriched, output_dir)
```

---

## 7. Relationship to Existing Pipeline

The existing `geojson_pipeline.py` does: convert → HUC mapping → coverage → enrich. The proposed pipeline adds classification and splitting **after** enrichment:

```
Existing:  Convert → HUC Map → Coverage → Enrich
Proposed:  Convert → HUC Map → Coverage → Enrich → Classify → Split
                                                    ↑new↑      ↑new↑
```

The classify step can reuse all enrichment results. Features already enriched with `psgc_id` can be classified by looking up the PSGC record's `type` field — no additional `search_fuzzy` calls needed for the ~90% that match via PCODE.

---

## 8. Testing Strategy

### 8.1 Unit Tests

- `test_classifier.py`: Test each classification path with known entities
  - HUC: City of Baguio → should classify as `highly_urbanized_city`
  - ICC: City of Dagupan → should classify as `independent_component_city`
  - Municipality: Adams, Ilocos Norte → `municipality`
  - Ambiguous: "San Carlos" → verify correct type via context

### 8.2 Integration Tests

- Run full pipeline on `2023-10-24` (known good snapshot with existing enrich outputs)
- Verify feature counts per output file match PSGC counts:
  ```python
  assert len(hucs_geojson["features"]) == 33
  assert len(iccs_geojson["features"]) == 6
  assert len(component_cities_geojson["features"]) == 111
  ```
- Verify no feature is lost: sum of all output files = total input features (minus non-admin)

### 8.3 Regression

- Compare `hierarchical/barangays.geojson` psgc_id set against existing `enriched/adm4.geojson` psgc_id set
- Coverage should be ≥ existing coverage
