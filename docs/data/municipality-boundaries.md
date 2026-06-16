---
title: Philippine Municipality Boundaries GeoJSON (PSGC)
description: Download Philippine municipality boundaries (1,485 polygons) as GeoJSON enriched with PSGC codes from NAMRIA shapefiles and PSA PSGC snapshots.
---

# Philippine municipality boundaries GeoJSON

Download **Philippine municipality boundaries** as GeoJSON, each polygon enriched with its
**PSGC code**. Snapshot `2023-10-24` contains 1,485 municipality polygons.

## Download

**1. Hierarchical** (curated / recommended) — per-class extract (municipalities only):

```bash
curl -LO https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2023-10-24/municipalities.geojson
```

**2. Enriched** (pipeline stage) — ADM3 file, in-repo only. Note: `adm3.geojson` contains municipalities
**and** cities combined (see [city boundaries](city-boundaries.md)):

```bash
curl -LO https://raw.githubusercontent.com/bendlikeabamboo/barangay-boundaries-repository/main/2023-10-24/enriched_t0p005/adm3.geojson
```

**3. Raw** (pipeline stage) — NAMRIA-converted, pre-enrichment (in-repo; also municipalities + cities
combined):

```bash
curl -LO https://raw.githubusercontent.com/bendlikeabamboo/barangay-boundaries-repository/main/2023-10-24/raw_t0p005/adm3.geojson
```

The enriched and raw files above are intermediate pipeline stages, browsable in-repo at
`2023-10-24/{raw,enriched,hierarchical}_t0p005/`. See
[Releases & versioning](../index.md#releases-versioning) for the `v<YYYY-MM-DD>` tag convention.

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
