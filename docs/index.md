---
title: Philippine Barangay Boundaries GeoJSON & PSGC RDF
description: Download enriched Philippine barangay, municipality, city, province, and region boundaries as GeoJSON, enriched with canonical PSGC codes from PSA snapshots and NAMRIA shapefiles.
---

# Philippine Barangay Boundaries GeoJSON & PSGC RDF

**Enriched Philippine administrative boundaries** as GeoJSON — barangays, municipalities, cities,
provinces, and regions — each polygon annotated with its canonical **PSGC code**, name, and status.
Generated from **PSA** Philippine Standard Geographic Code snapshots and **NAMRIA**
administrative-boundary shapefiles, with the full quarterly change history published as
**W3C ORG RDF linked data**.

- **Coverage:** 99.945% PSGC ↔ NAMRIA pcode match (snapshot `2023-10-24`)
- **Barangays:** 42,026 polygons · **Provinces:** 82 · **Regions:** 17
- **History:** 17 quarterly snapshots (2021-08-19 → 2026-04-13)
- **License:** MIT (code); PSA & NAMRIA credited for data

[Download from GitHub Releases :material-download:](https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases){ .md-button .md-button--primary }
[View on GitHub :fontawesome-brands-github:](https://github.com/bendlikeabamboo/barangay-boundaries-repository){ .md-button }

## Download the data

Prebuilt bundles and individual GeoJSON files are published on
[GitHub Releases](https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases).

| Bundle | Contents | Format |
|--------|----------|--------|
| `barangay-boundaries-2023-10-24-enriched.zip` | `adm0`–`adm4.geojson`, PSGC-enriched | GeoJSON |
| `barangay-boundaries-2023-10-24-hierarchical.zip` | per-class extracts (barangays, provinces, HUCs, …) | GeoJSON |
| `manifest.json` | MD5 / SHA-256 / size / feature count per file | JSON |
| `delta.{ttl,nt,jsonld}` | PSGC change-history RDF (per snapshot) | RDF / ORG |

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
NAMRIA shapefile boundaries with PSGC codes to produce enriched GeoJSON. See the
[PSGC code structure](psgc.md) and [HUC mapping](huc-mapping.md) references, or the
[architecture notes](https://github.com/bendlikeabamboo/barangay-boundaries-repository/blob/main/AGENTS.md).

---

<!-- JSON-LD structured data: Dataset schema for Google Dataset Search. -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Dataset",
  "name": "Philippine Barangay Boundaries GeoJSON with PSGC Codes",
  "description": "Enriched Philippine administrative boundaries (barangay, municipality, city, province, region) as GeoJSON, with each polygon annotated with its canonical Philippine Standard Geographic Code (PSGC). Derived from PSA PSGC snapshots and NAMRIA administrative-boundary shapefiles (v2023-11-06). Includes a quarterly PSGC change history published as W3C ORG RDF linked data across 17 snapshots from 2021-08-19 to 2026-04-13.",
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
      "name": "Enriched GeoJSON bundle (ADM0–ADM4)",
      "encodingFormat": "application/zip+json",
      "contentUrl": "https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/tag/v2023-10-24"
    },
    {
      "@type": "DataDownload",
      "name": "Barangay boundaries GeoJSON (ADM4)",
      "encodingFormat": "application/geo+json",
      "contentUrl": "https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2023-10-24/adm4.geojson"
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
