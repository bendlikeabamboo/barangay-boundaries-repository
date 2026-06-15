---
title: Philippine Region Boundaries GeoJSON (PSGC)
description: Download all 17 Philippine region boundaries as GeoJSON enriched with PSGC codes, derived from NAMRIA shapefiles and PSA PSGC snapshots.
---

# Philippine region boundaries GeoJSON

Download **all 17 Philippine region boundaries** (including NCR, BARMM, and the provinces-acting-as
regions) as GeoJSON, each polygon tagged with its **PSGC code**.

## Download

```bash
curl -LO https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2023-10-24/hierarchical/regions.geojson
```

## Coverage

| Metric | Value |
|--------|------:|
| PSGC regions | 17 |
| Polygons | 17 |
| Matched | 17 |
| Coverage | 100.000% |

Regions are ADM1-level units. Each region's PSGC code occupies the first two digits (`PP`) of the
10-digit PSGC hierarchy — see [PSGC code structure](../psgc.md).
