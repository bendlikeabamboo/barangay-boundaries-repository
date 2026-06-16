---
title: Philippine City Boundaries GeoJSON (PSGC) — HUC, ICC, Component
description: Download Philippine city boundaries (highly urbanized, independent component, and component cities) as GeoJSON enriched with PSGC codes, with HUC mapping handled.
---

# Philippine city boundaries GeoJSON

Philippine cities are split by legal class into separate GeoJSON extracts, each enriched with
**PSGC codes**. The class split matters because **Highly Urbanized Cities (HUCs)** and Independent
Component Cities report to the region, not a province — see [HUC mapping](../huc-mapping.md).

## Download

**1. Hierarchical** (curated / recommended) — cities split by legal class:

```bash
# Highly Urbanized Cities (34) — e.g. Quezon City, Makati, Davao
curl -LO https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2023-10-24/highly_urbanized_cities.geojson

# Independent Component Cities (6)
curl -LO https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2023-10-24/independent_component_cities.geojson

# Component Cities (110)
curl -LO https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2023-10-24/component_cities.geojson
```

**2. Enriched** (pipeline stage) — ADM3 file, in-repo only. Note: `adm3.geojson` mixes all cities with
municipalities, with no class separation:

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

## Counts (2023-10-24)

| Class | Features | Exact | HUC map | Fuzzy |
|-------|---------:|-----:|--------:|------:|
| Highly Urbanized City | 34 | 31 | 1 | 2 |
| Independent Component City | 6 | 6 | 0 | 0 |
| Component City | 110 | 110 | 0 | 0 |
| **Total cities** | **150** | | | |

## Coverage notes

- All cities also appear at ADM3 (`adm3.geojson`) and ADM2-level enrichment handles the HUC
  province-mismatch via `huc_adm2_mapping.json`.
- 1 component city (City of Isabela, Basilan) has no NAMRIA polygon.
