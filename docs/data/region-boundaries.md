---
title: Philippine Region Boundaries GeoJSON (PSGC)
description: Download all 17 Philippine region boundaries as GeoJSON enriched with PSGC codes, derived from NAMRIA shapefiles and PSA PSGC snapshots.
---

# Philippine region boundaries GeoJSON

Download **all 17 Philippine region boundaries** (including NCR, BARMM, and the provinces-acting-as
regions) as GeoJSON, each polygon tagged with its **PSGC code**.

## Download

**1. Hierarchical** (curated / recommended) — per-class extract:

```bash
curl -LO https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2026.4.13.0/regions.geojson
```

**2. Enriched** (pipeline stage) — ADM1 file with PSGC codes (in-repo only):

```bash
curl -LO https://raw.githubusercontent.com/bendlikeabamboo/barangay-boundaries-repository/main/2023-10-24/enriched_t0p005/adm1.geojson
```

**3. Raw** (pipeline stage) — NAMRIA-converted, pre-enrichment (in-repo):

```bash
curl -LO https://raw.githubusercontent.com/bendlikeabamboo/barangay-boundaries-repository/main/2023-10-24/raw_t0p005/adm1.geojson
```

The enriched and raw files above are intermediate pipeline stages, browsable in-repo at
`2023-10-24/{raw,enriched,hierarchical}_t0p005/`. See
[Releases & versioning](../index.md#releases-versioning) for the `v<YYYY-MM-DD>` tag convention.

## Coverage

| Metric | Value |
|--------|------:|
| PSGC regions | 17 |
| Polygons | 17 |
| Matched | 17 |
| Coverage | 100.000% |

Regions are ADM1-level units. Each region's PSGC code occupies the first two digits (`PP`) of the
10-digit PSGC hierarchy — see [PSGC code structure](../psgc.md).
