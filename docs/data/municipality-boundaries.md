---
title: Philippine Municipality Boundaries GeoJSON (PSGC)
description: Download Philippine municipality boundaries (1,485 polygons) as GeoJSON enriched with PSGC codes from NAMRIA shapefiles and PSA PSGC snapshots.
---

# Philippine municipality boundaries GeoJSON

Download **Philippine municipality boundaries** as GeoJSON, each polygon enriched with its
**PSGC code**. Snapshot `2023-10-24` contains 1,485 municipality polygons.

## Download

```bash
curl -LO https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2023-10-24/hierarchical/municipalities.geojson
```

## Coverage

| Metric | Value |
|--------|------:|
| PSGC municipalities | 1,485 |
| Polygons | 1,485 |
| Exact matches | 1,467 |
| Fuzzy matches | 18 |

Municipalities are ADM3-level units; cities are published separately by class (see
[city boundaries](city-boundaries.md)).

## Properties

Each feature carries `psgc_code` (10-digit, municipality segment `PPCCCMMLL0`), `psgc_name`,
`psgc_status`, `match_confidence`, and the source NAMRIA attributes.
