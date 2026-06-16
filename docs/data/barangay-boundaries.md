---
title: Philippine Barangay Boundaries GeoJSON (PSGC)
description: Download all 42,026 Philippine barangay boundaries as a single GeoJSON file enriched with PSGC codes, derived from NAMRIA shapefiles and PSA PSGC snapshots.
---

# Philippine barangay boundaries GeoJSON

Download **all Philippine barangay boundaries** as one GeoJSON file, every polygon tagged with its
canonical **PSGC code**. With 42,026 barangay polygons (snapshot `2023-10-24`), this is the
lowest-level administrative boundary dataset for the Philippines.

## Download

**1. Hierarchical** (curated / recommended) — per-class extract:

```bash
curl -LO https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2023-10-24/barangays.geojson
```

**2. Enriched** (pipeline stage) — ADM4 file with PSGC codes (in-repo only):

```bash
curl -LO https://raw.githubusercontent.com/bendlikeabamboo/barangay-boundaries-repository/main/2023-10-24/enriched_t0p005/adm4.geojson
```

**3. Raw** (pipeline stage) — NAMRIA-converted, pre-enrichment (in-repo):

```bash
curl -LO https://raw.githubusercontent.com/bendlikeabamboo/barangay-boundaries-repository/main/2023-10-24/raw_t0p005/adm4.geojson
```

The enriched and raw files above are intermediate pipeline stages, browsable in-repo at
`2023-10-24/{raw,enriched,hierarchical}_t0p005/`. See
[Releases & versioning](../index.md#releases-versioning) for the `v<YYYY-MM-DD>` tag convention.

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
