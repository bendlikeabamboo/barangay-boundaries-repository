---
title: Philippine Barangay Boundaries GeoJSON & PSGC RDF
description: Download curated hierarchical Philippine barangay, municipality, city, province, and region boundaries as per-class GeoJSON, enriched with canonical PSGC codes from PSA snapshots and NAMRIA shapefiles.
---

# Philippine Barangay Boundaries GeoJSON & PSGC RDF

**Curated hierarchical Philippine administrative boundaries** as GeoJSON — barangays, municipalities,
and cities split by legal class (highly urbanized, independent component, component), plus provinces,
regions, and special geographic areas — each polygon annotated with its canonical **PSGC code**, name,
and status. Generated from **PSA** Philippine Standard Geographic Code snapshots and **NAMRIA**
administrative-boundary shapefiles, with the full quarterly change history published as
**W3C ORG RDF linked data**. The `enriched` (`adm0`–`adm4`) and `raw` NAMRIA-converted files are kept
as intermediate pipeline stages.

- **Coverage:** 99.945% PSGC ↔ NAMRIA pcode match (snapshot `2023-10-24`)
- **Barangays:** 42,026 polygons · **Provinces:** 82 · **Regions:** 17
- **History:** 17 quarterly snapshots (2021-08-19 → 2026-04-13)
- **License:** MIT (code); PSA & NAMRIA credited for data

[Download from GitHub Releases :material-download:](https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases){ .md-button .md-button--primary }
[View on GitHub :fontawesome-github:](https://github.com/bendlikeabamboo/barangay-boundaries-repository){ .md-button }

## Download the data

The curated **hierarchical per-class GeoJSON** is published on
[GitHub Releases](https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases) as a
bundle, individual per-class files, and a checksum manifest.

| Asset / file | Contents | Format |
|---------------|----------|--------|
| `barangay-boundaries-2023-10-24-hierarchical.zip` | per-class extracts (barangays, provinces, HUC/ICC/component cities, …) | GeoJSON |
| `barangays.geojson`, `provinces.geojson`, … | individual per-class extracts | GeoJSON |
| `manifest.json` | MD5 / SHA-256 / size / feature count per file | JSON |
| `delta.{ttl,nt,jsonld}` | PSGC change-history RDF (per snapshot) | RDF / ORG |
| `enriched_t0p005/adm0`–`adm4.geojson` | intermediate enrichment stage (in-repo) | GeoJSON |
| `raw_t0p005/adm0`–`adm4.geojson` | NAMRIA-converted, pre-enrichment (in-repo) | GeoJSON |

## Data transformation tiers

The data flows through three tiers. **Hierarchical** is the curated, recommended end product;
**enriched** and **raw** are the intermediate transformation stages, documented for traceability.

- **Hierarchical** (curated / recommended) — per-class GeoJSON extracts (`barangays`, `provinces`,
  HUC/ICC/component cities, …). Released as `*-hierarchical.zip` and individual `<class>.geojson` files.
- **Enriched** (pipeline stage) — `adm0`–`adm4.geojson` with each polygon annotated with its
  `psgc_code`, `psgc_name`, and `psgc_status`. In-repo at `enriched_t0p005/`; feeds the classifier.
- **Raw** (pipeline stage) — NAMRIA shapefiles converted to GeoJSON, before PSGC enrichment. In-repo
  only at
  [`2023-10-24/raw_t0p005/`](https://github.com/bendlikeabamboo/barangay-boundaries-repository/tree/main/2023-10-24/raw_t0p005)
  via `raw.githubusercontent.com`.

## Releases & versioning

Each PSGC snapshot is published two ways. Use whichever fits your workflow.

| Path | What you get | When to use |
|------|--------------|-------------|
| **GitHub Release** (versioned) | Pinned hierarchical bundle + individual per-class files + `manifest.json` | Citing a specific snapshot, reproducible downloads, checksum verification |
| **In-repo** (always current) | The committed GeoJSON under `2023-10-24/{raw,enriched,hierarchical}_t0p005/`, fetched via `raw.githubusercontent.com` | Pulling the latest tip of `main`, scripting against individual files, browsing source |

### Version tags

Every snapshot maps to a git tag of the form **`v<YYYY.M.DD.PATCH>`** (e.g. `v2026.4.13.0`). Pushing such a
tag triggers the `Release` workflow, which builds and attaches the `*-hierarchical.zip` bundle, the
individual per-class `<class>.geojson` files, and `manifest.json` to the matching GitHub Release:

```bash
git tag v2026.4.13.0
git push origin v2026.4.13.0
```

Release assets are version-pinned to that snapshot and never change. The in-repo files track `main`,
so they reflect whatever is currently committed (typically the latest snapshot).

## What's in each admin level

| Level | Class | Features (2023-10-24) | Page |
|-------|-------|----------------------:|------|
| ADM0 | Country | 1 | — |
| ADM1 | Region | 17 | [Region boundaries](data/region-boundaries.md) |
| ADM2 | Province | 82 | [Province boundaries](data/province-boundaries.md) |
| ADM3 | Municipality | 1,485 | [Municipality boundaries](data/municipality-boundaries.md) |
| ADM3 | City (HUC + component + ICC) | 150 | [City boundaries](data/city-boundaries.md) |
| ADM4 | Barangay | 42,026 | [Barangay boundaries](data/barangay-boundaries.md) |

## Why this dataset

Government boundary sources publish shapefiles and codes separately. This dataset **joins them**:
every NAMRIA polygon is enriched with its authoritative **PSGC code**, so the boundaries can be
linked to any PSGC-keyed Philippine dataset (census, health, elections, finance). It also publishes
the **17-snapshot change history** as RDF, making it possible to track how barangays were created,
merged, split, renamed, or transferred across quarters.

## How it was built

The `brgybnd` CLI converts PSA PSGC Excel/PDF snapshots into RDF (W3C ORG ontology) and matches
NAMRIA shapefile boundaries with PSGC codes to produce the curated hierarchical per-class GeoJSON
(via an `enriched` intermediate stage). See the
[PSGC code structure](psgc.md) and [HUC mapping](huc-mapping.md) references, or the
[architecture notes](https://github.com/bendlikeabamboo/barangay-boundaries-repository/blob/main/AGENTS.md).

---

<!-- JSON-LD structured data: Dataset schema for Google Dataset Search. -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Dataset",
  "name": "Philippine Barangay Boundaries GeoJSON with PSGC Codes",
  "description": "Curated hierarchical Philippine administrative boundaries (barangay, municipality, city classes, province, region) as per-class GeoJSON, with each polygon annotated with its canonical Philippine Standard Geographic Code (PSGC). Derived from PSA PSGC snapshots and NAMRIA administrative-boundary shapefiles (v2023-11-06). Includes a quarterly PSGC change history published as W3C ORG RDF linked data across 17 snapshots from 2021-08-19 to 2026-04-13.",
  "url": "https://github.com/bendlikeabamboo/barangay-boundaries-repository",
  "creator": {
    "@type": "Person",
    "name": "Manuel Balmeo",
    "@id": "https://orcid.org/0000-0003-4815-858X"
  },
  "author": {
    "@type": "Person",
    "name": "Manuel Balmeo",
    "@id": "https://orcid.org/0000-0003-4815-858X"
  },
  "license": "https://spdx.org/licenses/MIT.html",
  "isAccessibleForFree": true,
  "keywords": [
    "Philippines",
    "barangay",
    "PSGC",
    "GeoJSON",
    "boundaries",
    "NAMRIA",
    "shapefile",
    "administrative boundaries",
    "RDF",
    "linked data",
    "W3C ORG",
    "provinces",
    "municipalities",
    "cities"
  ],
  "spatialCoverage": {
    "@type": "Place",
    "name": "Philippines",
    "geo": {
      "@type": "GeoShape",
      "box": "4.5 116.9 21.2 126.6"
    }
  },
  "temporalCoverage": "2021-08-19/2026-04-13",
  "inLanguage": "en",
  "distribution": [
    {
      "@type": "DataDownload",
      "name": "Curated hierarchical per-class GeoJSON bundle",
      "encodingFormat": "application/zip+json",
      "contentUrl": "https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/tag/v2026.4.13.0"
    },
    {
      "@type": "DataDownload",
      "name": "Barangay boundaries GeoJSON (curated per-class extract)",
      "encodingFormat": "application/geo+json",
      "contentUrl": "https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2026.4.13.0/barangays.geojson"
    },
    {
      "@type": "DataDownload",
      "name": "Enriched GeoJSON (ADM0–ADM4, intermediate pipeline stage)",
      "encodingFormat": "application/geo+json",
      "contentUrl": "https://github.com/bendlikeabamboo/barangay-boundaries-repository/tree/main/2023-10-24/enriched_t0p005"
    },
    {
      "@type": "DataDownload",
      "name": "Raw NAMRIA-converted GeoJSON (pre-enrichment, intermediate stage)",
      "encodingFormat": "application/geo+json",
      "contentUrl": "https://github.com/bendlikeabamboo/barangay-boundaries-repository/tree/main/2023-10-24/raw_t0p005"
    },
    {
      "@type": "DataDownload",
      "name": "PSGC change-history RDF",
      "encodingFormat": "text/turtle",
      "contentUrl": "https://github.com/bendlikeabamboo/barangay-boundaries-repository"
    }
  ],
  "citation": "https://github.com/bendlikeabamboo/barangay-boundaries-repository",
  "publisher": {
    "@type": "Person",
    "name": "Manuel Balmeo",
    "@id": "https://orcid.org/0000-0003-4815-858X"
  }
}
</script>
