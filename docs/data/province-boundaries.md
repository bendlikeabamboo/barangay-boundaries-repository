---
title: Philippine Province Boundaries GeoJSON (PSGC)
description: Download all 82 Philippine province boundaries as GeoJSON enriched with PSGC codes, derived from NAMRIA shapefiles and PSA PSGC snapshots.
---

# Philippine province boundaries GeoJSON

Download **all 82 Philippine province boundaries** as GeoJSON, each polygon tagged with its
canonical **PSGC code**. Snapshot `2023-10-24`.

## Download

**1. Hierarchical** (curated / recommended) — per-class extract:

```bash
curl -LO https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2026.4.13.0/provinces.geojson
```

**2. Enriched** (pipeline stage) — ADM2 file, in-repo only (provinces plus province-placed HUC/MM-district
units):

```bash
curl -LO https://raw.githubusercontent.com/bendlikeabamboo/barangay-boundaries-repository/main/2023-10-24/enriched_t0p005/adm2.geojson
```

**3. Raw** (pipeline stage) — NAMRIA-converted, pre-enrichment (in-repo):

```bash
curl -LO https://raw.githubusercontent.com/bendlikeabamboo/barangay-boundaries-repository/main/2023-10-24/raw_t0p005/adm2.geojson
```

The enriched and raw files above are intermediate pipeline stages, browsable in-repo at
`2023-10-24/{raw,enriched,hierarchical}_t0p005/`. See
[Releases & versioning](../index.md#releases-versioning) for the `v<YYYY-MM-DD>` tag convention.

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
