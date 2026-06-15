---
title: Philippine Province Boundaries GeoJSON (PSGC)
description: Download all 82 Philippine province boundaries as GeoJSON enriched with PSGC codes, derived from NAMRIA shapefiles and PSA PSGC snapshots.
---

# Philippine province boundaries GeoJSON

Download **all 82 Philippine province boundaries** as GeoJSON, each polygon tagged with its
canonical **PSGC code**. Snapshot `2023-10-24`.

## Download

```bash
curl -LO https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2023-10-24/hierarchical/provinces.geojson
```

Or the ADM2 file (provinces plus province-placed units):

```bash
curl -LO https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2023-10-24/adm2.geojson
```

## Coverage

| Metric | Value |
|--------|------:|
| PSGC provinces | 82 |
| Polygons | 82 |
| Matched | 82 |
| Coverage | 100.000% |

## Note on ADM2

NAMRIA's ADM2 layer contains 88 features: the 82 provinces plus province-level placements of some
HUCs and Metro Manila districts. The `huc_adm2_mapping.json` file reconciles these to PSGC parents.
