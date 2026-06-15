---
title: Philippine Barangay Boundaries GeoJSON (PSGC)
description: Download all 42,026 Philippine barangay boundaries as a single GeoJSON file enriched with PSGC codes, derived from NAMRIA shapefiles and PSA PSGC snapshots.
---

# Philippine barangay boundaries GeoJSON

Download **all Philippine barangay boundaries** as one GeoJSON file, every polygon tagged with its
canonical **PSGC code**. With 42,026 barangay polygons (snapshot `2023-10-24`), this is the
lowest-level administrative boundary dataset for the Philippines.

## Download

```bash
curl -LO https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2023-10-24/adm4.geojson
```

Or grab the per-class extract:

```bash
curl -LO https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2023-10-24/hierarchical/barangays.geojson
```

## Coverage (ADM4)

| Metric | Value |
|--------|------:|
| PSGC barangays | 42,010 |
| NAMRIA polygons | 41,825 |
| Matched | 41,803 |
| Coverage | 99.947% |
| Exact matches | 38,771 |
| Fuzzy matches | 3,255 |

## Properties per feature

Each barangay feature includes `psgc_code` (10-digit), `psgc_name`, `psgc_status`,
`match_confidence`, plus the original NAMRIA attributes (e.g. `ADM4_EN`, `ADM4_PCODE`).

## Use it

Load into geopandas, QGIS, or any GeoJSON reader, then join on `psgc_code` to census, health,
election, or financial data keyed by Philippine Standard Geographic Code.

## Limitations

- ~198 PSGC barangays (mostly in BARMM and Metro Manila) have no NAMRIA polygon.
- 6 features could not be resolved to a PSGC entity (`unresolved.geojson`).
