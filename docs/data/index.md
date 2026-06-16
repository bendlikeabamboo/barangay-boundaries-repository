---
title: Data Overview — Philippine Boundaries GeoJSON
description: Overview of the curated hierarchical Philippine administrative boundary GeoJSON datasets by class (region, province, city classes, municipality, barangay) with PSGC codes.
---

# Philippine administrative boundary data

The dataset's curated output is the **per-class (hierarchical) GeoJSON collection** — e.g. `barangays`,
`provinces`, `municipalities`, and cities split by legal class (highly urbanized, independent component,
component). Every polygon is enriched with its canonical **PSGC code**, name, and status. Boundaries
originate from NAMRIA shapefiles (v2023-11-06); PSGC codes from PSA snapshots (latest: `2023-10-24`).

The full `adm0`–`adm4` **enriched** files and the pre-enrichment **raw** NAMRIA conversion are also
available as intermediate transformation stages of the pipeline that produces the hierarchical output.

## Data transformation tiers

| Tier | What it is | Where to get it |
|------|-----------|-----------------|
| **Hierarchical** (curated / recommended) | per-class GeoJSON extracts | release bundle `*-hierarchical.zip` + `releases/download/.../<file>.geojson` |
| **Enriched** (pipeline stage) | `adm0`–`adm4.geojson` with PSGC | in-repo `enriched_t0p005/` via `raw.githubusercontent.com` |
| **Raw** (pipeline stage) | NAMRIA-converted, pre-enrichment | in-repo [`2023-10-24/raw_t0p005/`](https://github.com/bendlikeabamboo/barangay-boundaries-repository/tree/main/2023-10-24/raw_t0p005) via `raw.githubusercontent.com` |

The pipeline is `raw` (NAMRIA shapefile → GeoJSON, no PSGC) → `enriched` (adds `psgc_code`/`name`/
`status`) → `hierarchical` (per-class extracts, the curated end product).

Every file is available two ways: as a **versioned GitHub Release** asset (pinned to a
`v<YYYY-MM-DD>` tag, with `manifest.json` checksums) or **in-repo** at `2023-10-24/{tier}_t0p005/`
via `raw.githubusercontent.com`. See [Releases & versioning](../index.md#releases-versioning) for the
tag convention.

## Coverage by level

| Level | File | Features | Matched | Coverage |
|-------|------|---------:|--------:|---------:|
| ADM0 | `adm0.geojson` | 1 | 1 | 100.000% |
| ADM1 Region | `adm1.geojson` | 17 | 17 | 100.000% |
| ADM2 Province | `adm2.geojson` | 88 | 88 | 100.000% |
| ADM3 Municipality/City | `adm3.geojson` | 1,626 | 1,624 | 99.877% |
| ADM4 Barangay | `adm4.geojson` | 41,825 | 41,803 | 99.947% |

Per-class extracts (hierarchical) split cities by class (highly urbanized, independent component,
component) and separate special geographic areas.

## Enriched properties

Each GeoJSON feature carries:

- `psgc_id` — stable entity URI
- `psgc_code` — 10-digit Philippine Standard Geographic Code
- `psgc_name` — canonical name
- `psgc_status` — e.g. `existing`
- `match_confidence` — `exact` | `huc_map` | `fuzzy`

## Download

Get any file from the
[2023-10-24 snapshot release](https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/tag/v2026.4.13.0).

Explore by level:
[Barangay](barangay-boundaries.md) ·
[Municipality](municipality-boundaries.md) ·
[City](city-boundaries.md) ·
[Province](province-boundaries.md) ·
[Region](region-boundaries.md)
