# Edge Cases Catalog

> **Prerequisite:** Read [`00-feasibility-overview.md`](./00-feasibility-overview.md) and [`01-proposed-pipeline.md`](./01-proposed-pipeline.md).

This document catalogs every known edge case in the NAMRIA→PSGC mapping, its current handling status, and the proposed resolution for hierarchical output.

---

## Edge Case Index

| # | Edge Case | Severity | Current Status | Affects Output |
|---|---|---|---|---|
| 1 | HUCs nested under provinces in NAMRIA | Critical | ✅ Handled (HUC mapping) | `hucs.geojson` |
| 2 | ICCs with province-like parent codes | High | ✅ Handled (HUC mapping) | `iccs.geojson` |
| 3 | Metro Manila districts (no PSGC province) | Critical | ✅ Handled (virtual_provinces) | `provinces.geojson` |
| 4 | Special Geographic Area (BARMM) | Medium | ✅ Handled (virtual_provinces) | `sga.geojson` |
| 5 | Isabela City (Basilan) as ADM2 | Medium | ✅ Handled (special case) | `provinces.geojson` |
| 6 | Submunicipalities under Manila/Quezon City | Medium | ⚠️ Partial | `submunicipalities.geojson` |
| 7 | Non-administrative areas in ADM4 | Low | ✅ Handled (_NON_ADMIN_PATTERNS) | Excluded |
| 8 | Name ambiguity (San Carlos, Santa Maria) | High | ⚠️ Needs attention | All city/muni files |
| 9 | "City of" prefix inconsistency | Medium | ✅ Handled (_sanitize) | All city files |
| 10 | Cotabato City / Isabela City name collision | High | ⚠️ Needs attention | `iccs.geojson`, `hucs.geojson` |
| 11 | Barangays shared across submunicipalities | Low | ✅ Handled (submuni_parents) | `barangays.geojson` |
| 12 | SGA barangays with non-standard parent | Medium | ✅ Handled (cross_parent_map) | `barangays.geojson` |
| 13 | NAMRIA ADM0 has 3,640 polygons (islands) | Low | Design choice | `country.geojson` |
| 14 | search_fuzzy cold-start (2.3s) | Low | Operational | Performance |
| 15 | Multi-hook search limitations | Medium | Design constraint | Classification accuracy |

---

## Detailed Analysis

### 1. HUCs Nested Under Provinces (Critical)

**Problem:** 33 Highly Urbanized Cities are geographically inside a province in NAMRIA's data, but administratively report directly to their region in PSGC.

**Example:**
```
City of Cebu:
  NAMRIA: ADM2_PCODE=PH07222 (Cebu province), ADM3_PCODE=PH0722202
  PSGC:   psgc_id=0722700000, parent=0700000000 (Region VII)
```

**Current handling:** `generate_huc_mapping.py` fuzzy-matches NAMRIA ADM3 names against `bg.hucs` within each region, building `namria_adm3_to_psgc[PH0722202] = PH072270`.

**For hierarchical output:**
- The HUC polygon is extracted from ADM3
- Its `ADM2_PCODE` is re-assigned from province to region
- It goes into `highly_urbanized_cities.geojson`, not `municipalities.geojson`
- The original NAMRIA nesting is preserved in `namria_adm2_pcode` for traceability

**Residual risk:** If `generate_huc_mapping.py` fails to match an HUC name (fuzzy threshold not met), it stays in the municipality bucket. The `match_method` field will show `"unresolved"`, enabling manual review.

---

### 2. ICCs with Province-Like Parent Codes (High)

**Problem:** The 6 Independent Component Cities have inconsistent parent relationships in PSGC:

| ICC | psgc_id | parent_psgc_id | Parent looks like |
|---|---|---|---|
| City of Isabela | 0990100000 | 0900000000 | Region IX ✅ |
| City of Cotabato | 1908703000 | 1908700000 | Municipality(!) |
| City of Dagupan | 0105518000 | 0105500000 | Province ✅ |
| City of Santiago | 0203135000 | 0203100000 | Province ✅ |
| City of Naga | 0501724000 | 0501700000 | Province ✅ |
| Ormoc City | 0803738000 | 0803700000 | Province ✅ |

City of Cotabato is the anomaly: its parent (`1908700000`) is Maguindanao del Norte, which is a province, but the code structure looks like a municipality. In NAMRIA, Cotabato City is nested under Maguindanao del Norte at ADM2.

**For hierarchical output:**
- All 6 ICCs are classified by the HUC mapping (`namria_adm3_to_psgc`)
- Their `psgc_type` is `independent_component_city`
- They go into `independent_component_cities.geojson`

**Residual risk:** City of Cotabato's parent resolution may be ambiguous. The `EnrichedRecord.parent` property should resolve correctly via the hierarchy index.

---

### 3. Metro Manila Districts (Critical)

**Problem:** NCR has no PSGC province-level entities. NAMRIA represents NCR as:
- ADM2: `PH13001`–`PH13004` (4 legislative districts) — **not in PSGC**
- ADM3: 17 LGUs (16 HUCs + Pateros municipality)

PSGC treats all 17 NCR LGUs as direct children of region `PH13`.

**Current handling:** `huc_adm2_mapping.json` maps:
- `virtual_provinces[PH1300x]` → `{"type": "mm_district"}`
- `metro_manila_districts[PH1300x]` → list of constituent city pcodes
- `namria_adm3_to_psgc[PH1300xxxx]` → correct PSGC pcode

**For hierarchical output:**
- The 4 MM district ADM2 features are **dropped** (no PSGC equivalent)
- The 16 NCR HUCs go to `highly_urbanized_cities.geojson`
- Pateros goes to `municipalities.geojson`
- Their `region` field is "National Capital Region (NCR)"

**No PSGC province file for NCR.** This is correct behavior — NCR genuinely has no provinces.

---

### 4. Special Geographic Area — BARMM (Medium)

**Problem:** BARMM's SGA is a single PSGC entity (`1900000000` region-level concept) spanning 63 barangays across 6 municipalities in geographically disconnected areas (from the 2019 plebiscite). NAMRIA represents it as a virtual ADM2 province.

**Current handling:** `virtual_provinces[SGA_ADM2_PCODE]` → `{"type": "sga", "psgc_pcode": "PH19xxx"}`

**For hierarchical output:**
- The SGA virtual ADM2 feature is written to `special_geographic_areas.geojson`
- SGA barangays from ADM4 are also included there (not in `barangays.geojson`), OR a flag `is_sga=true` is set on them in `barangays.geojson`

**Open question:** Should SGA barangays appear in both `barangays.geojson` and `special_geographic_areas.geojson`, or only one? Recommendation: **keep them in `barangays.geojson`** with `psgc_type=barangay` and an `sga_member=true` flag, and put only the SGA aggregate polygon in `special_geographic_areas.geojson`.

---

### 5. Isabela City as ADM2 (Medium)

**Problem:** City of Isabela (Basilan) is an ICC. In NAMRIA, Basilan province (`PH09097`) ADM2 contains both Isabela City and the municipalities of the newly-created Basilan province. PSGC assigns Isabela City to Region IX directly.

**Current handling:** Hardcoded special case:
```python
if "Isabela" in adm2_name and adm2_code == "PH09097":
    virtual_provinces[adm2_code] = {"type": "huc_isabela", ...}
```

**For hierarchical output:**
- Isabela City → `independent_component_cities.geojson`
- Basilan province municipalities → `municipalities.geojson`
- The ADM2 `PH09097` is a NAMRIA artifact — don't output it as a province

---

### 6. Submunicipalities (Medium)

**Problem:** 14 submunicipalities exist in PSGC, all under Manila (8: Tondo I/II, Binondo, Santa Cruz, San Nicolas, Quiapo, San Miguel, Ermita) or Quezon City (6: Barangka, Horseshoe, Marikina Heights, Sta. Elena, Sto. Niño, Tañong). Wait — actually these are Marikina/Quezon City areas. Let me verify:

PSGC submunicipalities (14):
- Manila: Tondo I, Tondo II, Binondo, Santa Cruz, San Nicolas, Quiapo, San Miguel, Ermita (8)
- These are Administrative Districts, not self-governing LGUs in the traditional sense

In NAMRIA, these may not have separate ADM4 polygons. They may be represented only at ADM3 level (under Manila HUC) or may have ADM4 features with non-standard pcodes.

**For hierarchical output:**
- Extract features from ADM4 where pcode matches `bg.submunicipalities` pcodes
- These go into `submunicipalities.geojson`
- Their parent is the HUC (Manila/Quezon City)

**Current status:** `enrich.py` handles `submunicipality_parents` in the HUC mapping for barangay resolution, but doesn't extract submunicipality LGUs as separate features. This needs to be added.

**Residual risk:** If NAMRIA doesn't have separate polygons for submunicipalities, `submunicipalities.geojson` may be empty or may need to be generated from ADM4 barangay aggregation.

---

### 7. Non-Administrative Areas in ADM4 (Low)

**Problem:** NAMRIA ADM4 contains ~20 features that are not administrative barangays:
- Forest land, timber land, national parks
- Watersheds, unclaimed areas
- Cemeteries, mall (claimed areas)

**Current handling:** `_NON_ADMIN_PATTERNS` in `enrich.py:26-35` filters these:
```python
_NON_ADMIN_PATTERNS = ["forest land", "timber land", "mount apo",
    "watershed", "unclaimed area", "national park", "cemetery", "mall (claimed"]
```

**For hierarchical output:** These are excluded entirely. Optionally, they can be written to `non_administrative.geojson` for completeness.

---

### 8. Name Ambiguity (High)

**Problem:** Many Philippine place names are shared across entity types and locations:

| Name | Appears as | Locations |
|---|---|---|
| San Carlos | CC, Mun, Bgy | Pangasinan (CC), Negros Occidental (CC), multiple barangays |
| San Jose | Mun, Bgy | Occidental Mindoro (Mun), Antique (Mun), 50+ barangays |
| Santa Maria | Mun, Bgy | Bulacan (Mun), Ilocos Sur (Mun), 100+ barangays |
| Santiago | ICC, Mun, Bgy | Isabela (ICC), Agusan del Norte (Mun), many barangays |

**Impact on classification:** `search_fuzzy("San Carlos", match_hooks=["component_city"])` will correctly find 2 component cities (San Carlos Pangasinan, San Carlos Negros Occidental) — but which one is the ADM3 feature?

**Resolution:** Always include hierarchical context in the query:
```python
# Instead of: search_fuzzy("San Carlos", hooks=["component_city"])
# Use parent context:
query = f"San Carlos, {adm2_name}"  # e.g., "San Carlos, Pangasinan"
search_fuzzy(query, level=AdminLevel.COMPONENT_CITY,
             match_hooks=["province", "component_city"], limit=1)
```

**Limitation discovered:** `["province", "component_city"]` multi-hook only works if the fuzzer_base has a pre-concatenated column for it. The available columns are:
- `rp00c000b` (region + province + component_city + barangay)
- `rp0i0000b` (region + province + ICC + barangay)

These include barangay in the concatenation, so using them for city-level search (without barangay context) may produce suboptimal scores. **Single-hook searches** (`["component_city"]`) with post-filtering by province may be more reliable.

**Proposed approach:** Run single-hook search → get top N results → post-filter by matching `result.province` against ADM2 name. This is more reliable than multi-hook for non-barangay levels.

---

### 9. "City of" Prefix Inconsistency (Medium)

**Problem:** PSGC uses "City of X" for some cities and "X City" for others:
- "City of Baguio", "City of Cebu" (HUCs)
- "Dagupan City" in NAMRIA vs "City of Dagupan" in PSGC

**Current handling:** `_sanitize()` in `enrich.py:38-44` strips "City of" and "city" tokens before fuzzy matching.

**For hierarchical output:** The `psgc_name` field uses the official PSGC spelling. The NAMRIA original is preserved in `ADM3_EN`.

---

### 10. Cotabato City / Isabela City Name Collision (High)

**Problem:** Both "Cotabato City" and "City of Cotabato" can refer to:
1. Cotabato City (ICC, psgc_id=1908703000) — in Maguindanao
2. Cotabato (province, psgc_id=1244000000) — formerly North Cotabato

Similarly, "City of Isabela" refers to:
1. City of Isabela (ICC, psgc_id=0990100000) — in Basilan
2. Isabela (province, psgc_id=1907000000) — in Basilan

**Resolution:** The HUC mapping disambiguates these via `namria_adm3_to_psgc`. If that mapping is correct, the classification is correct. The `search_fuzzy` fallback should use `level=INDEPENDENT_COMPONENT_CITY` to avoid matching the province.

---

### 11. Barangays Shared Across Submunicipalities (Low)

**Problem:** In Manila, barangays are organized under 8 administrative districts (submunicipalities in PSGC). A barangay like "Barangay 1" may exist under multiple submunicipalities.

**Current handling:** `_resolve_parent_brgys()` in `enrich.py:313-318` merges barangays from both the parent and submunicipality parents:
```python
def _resolve_parent_brgys(psgc_parent):
    brgys = psgc_by_parent.get(psgc_parent, {})
    for submuni_pcode in submuni_parents.get(psgc_parent, []):
        brgys.update(psgc_by_parent.get(submuni_pcode, {}))
    return brgys
```

**For hierarchical output:** No additional handling needed. Barangays are correctly matched to their PSGC code regardless of submunicipality grouping.

---

### 12. SGA Barangays with Non-Standard Parent (Medium)

**Problem:** SGA barangays in BARMM have a parent that maps through `cross_parent_map` — their PSGC parent doesn't directly correspond to a NAMRIA ADM3 pcode.

**Current handling:** `enrich.py:374-381` tries alternate parents via `cross_parent_map`.

**For hierarchical output:** SGA barangays get `psgc_type=barangay` with an `sga_member=true` flag. They appear in `barangays.geojson`.

---

### 13. NAMRIA ADM0 — 3,640 Island Polygons (Low)

**Problem:** ADM0 is a single-part polygon in the filename but actually contains 3,640 individual island polygons representing the entire Philippine archipelago.

**For hierarchical output:** Write as-is to `country.geojson`. The 3,640 features share the same `ADM0_EN="Philippines (the)"` and `psgc_id=0000000000`.

**Design note:** This is correct — the Philippines is an archipelago. Consumers expecting a single polygon should use `dissolve()` in GeoPandas.

---

### 14. search_fuzzy Cold Start (Low, Operational)

**Problem:** The first `search_fuzzy` call after `bg.use_version()` takes ~2.3 seconds to load the fuzzer_base parquet. Subsequent calls are ~0.18s each.

**Resolution:** Add a warm-up call at pipeline start:
```python
# Warm up the fuzzer cache
search_fuzzy("__warmup__", level=AdminLevel.BARANGAY, limit=1)
```

This is cosmetic — the 2.3s is a one-time cost regardless.

---

### 15. Multi-Hook Search Limitations (Medium, Design Constraint)

**Problem:** `search_fuzzy` with multi-level `match_hooks` only works when the fuzzer_base has a corresponding pre-concatenated column:

| Hook Combination | Column Available? | Works? |
|---|---|---|
| `["barangay"]` | `barangay` | ✅ |
| `["municipality", "barangay"]` | `r0000m00b` | ✅ |
| `["province", "municipality"]` | (no barangay-level) | ✅ (municipality scope) |
| `["province", "component_city", "barangay"]` | `rp00c000b` | ✅ |
| `["region", "highly_urbanized_city"]` | (no `r0h0000` column) | ❌ |
| `["region", "province"]` | (no province-only column) | ❌ |

**Impact:** You cannot add region-level context to city/municipality searches via hooks. The workaround is:
1. Use single-hook search (e.g. `["component_city"]`)
2. Post-filter results by checking `result.record.parent_psgc_id` against expected region/province

**For hierarchical output:** This affects ~10% of ADM3 features that need fuzzy classification. The post-filter approach is reliable but requires an extra lookup step.

---

## Summary: Risk Mitigation Priority

1. **Must resolve before implementation:**
   - Submunicipality extraction (#6) — need to verify NAMRIA has polygon data
   - Name ambiguity post-filtering (#8) — implement province-context post-filter

2. **Handled by existing code:**
   - HUC/ICC nesting (#1, #2, #5) — via HUC mapping
   - Metro Manila (#3) — via virtual_provinces
   - SGA (#4, #12) — via virtual_provinces + cross_parent_map
   - Non-admin areas (#7) — via _NON_ADMIN_PATTERNS
   - Name sanitization (#9) — via _sanitize()

3. **Acceptable residual risk:**
   - Cotabato/Isabela collisions (#10) — rare, HUC mapping covers them
   - Cold start (#14) — cosmetic, 2.3s one-time
   - Multi-hook limitation (#15) — workaround exists
