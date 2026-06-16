# Barangay Boundaries Repository — Philippine Barangay Boundaries GeoJSON & PSGC RDF

**Hierarchical per-class Philippine administrative boundaries (GeoJSON)** — barangays, municipalities,
and cities split by legal class (highly urbanized, independent component, component), plus provinces,
regions, and special geographic areas — each polygon annotated with its canonical **PSGC code**.
Generated from [PSA](https://psa.gov.ph/) Philippine Standard Geographic Code snapshots and
[NAMRIA](https://namria.gov.ph/) administrative-boundary shapefiles, with the full history of quarterly
PSGC changes published as a W3C ORG-ontology knowledge graph. The enriched `adm0`–`adm4` files and the
pre-enrichment raw NAMRIA conversion are preserved as intermediate pipeline stages.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://docs.astral.sh/ruff/)
[![CI](https://github.com/bendlikeabamboo/barangay-boundaries-repository/actions/workflows/ci.yml/badge.svg)](https://github.com/bendlikeabamboo/barangay-boundaries-repository/actions/workflows/ci.yml)
[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/bendlikeabamboo/barangay-boundaries-repository/release.yml?label=Release)
](https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases)
[![GitHub Repo stars](https://img.shields.io/github/stars/bendlikeabamboo/barangay-boundaries-repository)
](https://github.com/bendlikeabamboo/barangay-boundaries-repository)
![Snapshot](https://img.shields.io/badge/latest%20snapshot-2023--10--24-orange)

## What this is

This repository is both a **dataset** and the **toolchain** that produces it. The dataset's curated
output is the **hierarchical per-class GeoJSON collection** — one file per administrative class
(`barangays`, `provinces`, `municipalities`, `highly_urbanized_cities`, `independent_component_cities`,
`component_cities`, `special_geographic_areas`, …) — with each polygon annotated with its canonical
**PSGC code**, name, and status. These are produced from NAMRIA shapefiles enriched with PSA PSGC
data; the `enriched` (`adm0`–`adm4`) and `raw` NAMRIA-converted files are kept as intermediate stages
of the same pipeline. The toolchain (`brgybnd`) also ingests PSA PSGC Excel/PDF snapshots and emits RDF
linked data using the [W3C ORG ontology](https://www.w3.org/TR/vocab-org/) plus machine-readable deltas
across **17 quarterly snapshots** (2021-08-19 → 2026-04-13).

It is built for GIS analysts, researchers, journalists, and civic-tech projects who need
**authoritative, code-stable Philippine boundary data** that can be joined to any PSGC-keyed dataset.

## Key features

- **Hierarchical per-class extracts** — the curated end product: one GeoJSON per administrative class
  (`barangays`, `provinces`, `municipalities`, `highly_urbanized_cities`,
  `independent_component_cities`, `component_cities`, `special_geographic_areas`, …) with cities split
  by legal class and each polygon tagged with its canonical PSGC code.
- **PSGC pcode enrichment** — pipeline stage (`enriched_t0p005/`) that annotates every feature with
  `psgc_id`, `psgc_code`, `psgc_name`, `psgc_status`, and a `match_confidence` score
  (exact / HUC-map / fuzzy); this feeds the classifier that produces the hierarchical output.
- **GeoJSON per administrative level** — country (ADM0), region (ADM1), province (ADM2),
  municipality/city (ADM3), barangay (ADM4), simplified with Douglas–Peucker (tolerance `0.005°`).
- **17 quarterly snapshots** of PSGC change history as RDF (`delta.ttl` / `.nt` / `.jsonld`) with
  creation, deletion, transfer, merger, split, rename, and code-change events.
- **HUC mapping** — resolves the Highly-Urbanized-City / NAMRIA-province mismatch (see
  [The HUC problem](#the-huc-problem)).
- **99.945% pcode coverage** between PSGC and NAMRIA for the 2023-10-24 snapshot.

## Download the data

The **curated hierarchical per-class GeoJSON** is published as **GitHub Releases** — as a zipped
bundle, individual per-class files, and a checksum manifest. The enriched `adm*` files and raw
NAMRIA conversion are intermediate pipeline stages kept in-repo for traceability. See
[Releases](https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases).

The inaugural release **`v2026.4.13.0`** ships the fully processed `2023-10-24` snapshot:

| Asset | Contents | Tier |
|-------|----------|------|
| `barangay-boundaries-2023-10-24-hierarchical.zip` | per-class GeoJSON (barangays, provinces, regions, municipalities, HUC/ICC/component cities, …) | curated (recommended) |
| `barangays.geojson`, `provinces.geojson`, `regions.geojson`, … | individual per-class extracts | curated (recommended) |
| `manifest.json` | per-file MD5/SHA-256, size, feature count | — |
| `delta.{ttl,nt,jsonld}` | PSGC change-history RDF | — |
| `enriched_t0p005/adm{0..4}.geojson` | PSGC-enriched, pre-classification (in-repo only) | intermediate stage |
| `raw_t0p005/adm{0..4}.geojson` | NAMRIA-converted, pre-enrichment (in-repo only) | intermediate stage |

Or grab an individual per-class file directly, e.g.:

```bash
# All ~42,000 barangay polygons (curated per-class extract)
curl -LO https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/download/v2026.4.13.0/barangays.geojson
```

## Quick start

The CLI (`brgybnd`) converts PSA PSGC snapshots and NAMRIA shapefiles into enriched GeoJSON and
RDF. It is **GitHub-only** (not on PyPI); install directly from the repository with `uv`:

```bash
uv tool install git+https://github.com/bendlikeabamboo/barangay-boundaries-repository.git
```

Three example workflows:

```bash
# 1. Ingest a PSGC snapshot (datafile + changes + press release) for a given date
brgybnd ingest --date 2023-10-24

# 2. Convert NAMRIA shapefiles to simplified GeoJSON (ADM0–ADM4)
brgybnd convert-geo --levels 0,1,2,3,4 --tolerance 0.005

# 3. Build the curated per-class hierarchical GeoJSON (convert → enrich → classify → split)
brgybnd build-hierarchical --date 2023-10-24
```

Other commands: `brgybnd list`, `brgybnd process`, `brgybnd process-all`, `brgybnd delta`,
`brgybnd validate`, `brgybnd coverage`, `brgybnd enrich`. Run `brgybnd --help` for the full reference.

## Data coverage (snapshot 2023-10-24)

PSGC ↔ NAMRIA pcode matching, from `enriched_t0p005/summary.md`:

| Level | Meaning | PSGC entities | GeoJSON features | Matched | Coverage |
|-------|---------|--------------:|-----------------:|--------:|---------:|
| ADM0 | Country | 1 | 1 | 1 | 100.000% |
| ADM1 | Region | 17 | 17 | 17 | 100.000% |
| ADM2 | Province | 82 | 88 | 88 | 100.000% |
| ADM3 | Municipality / City | 1,644 | 1,626 | 1,624 | 99.877% |
| ADM4 | Barangay | 42,010 | 41,825 | 41,803 | 99.947% |
| **Total** | | **43,754** | **43,557** | **43,533** | **99.945%** |

Per-class feature counts (hierarchical extract, NAMRIA v2023-11-06):

| Class | Features |
|-------|---------:|
| Region | 17 |
| Province | 82 |
| Municipality | 1,485 |
| Component City | 110 |
| Independent Component City | 6 |
| Highly Urbanized City | 34 |
| Barangay | 42,026 |
| Special Geographic Area | 9 |

### Known limitations (represented honestly)

- **Submunicipalities**: NAMRIA ADM4 has no separate polygons for the 14 Manila submunicipalities,
  so `submunicipalities.geojson` is empty. Aggregation from barangays is out of scope.
- **6 unresolved features** (`unresolved.geojson`) and **20 non-administrative features** could not
  be classified to a standard PSGC level.
- **230 PSGC entities** (mostly barangays in BARMM and Metro Manila) have no NAMRIA polygon.

## PSGC code structure

The Philippine Standard Geographic Code is a **10-digit hierarchical identifier** of the form
`PPCCCMMLLL0`:

| Digits | Level | Example |
|--------|-------|---------|
| `PP` | Region | `1300000000` — National Capital Region |
| `PPCCC` | Province / HUC | `1339000000` — City of Makati |
| `PPCC CMM` | Municipality / City | `1339060000` — City of Makati (muni-level) |
| `PPCCCMMLLL` | Barangay | `1339060014` — a barangay of Makati |

A 9-digit **correspondence code** tracks entity identity across code changes (used to compute
deltas). See [PSGC reference](https://bendlikeabamboo.github.io/barangay-boundaries-repository/psgc/)
for the full breakdown.

## The HUC problem

**Highly Urbanized Cities (HUCs)** are administratively independent of any province, so the PSGC
records their parent as the **region**. NAMRIA, however, draws HUC polygons **inside** their
geographic province. A naive parent-lookup therefore misassigns HUCs.

This repository resolves the mismatch with `namria/huc_adm2_mapping.json` (generated by
`generate_huc_mapping.py`), consumed by both `coverage.py` and `enrich.py`. Metro Manila is handled
separately: it has no PSGC province-level units, so NAMRIA's four NCR legislative districts are
mapped as **virtual provinces** of type `mm_district`.

Read the full explainer → [HUC mapping](https://bendlikeabamboo.github.io/barangay-boundaries-repository/huc-mapping/).

## Outputs / file map

Each snapshot directory (`YYYY-MM-DD/`) contains:

| File | Description |
|------|-------------|
| `delta.ttl` / `.nt` / `.jsonld` | PSGC change-history RDF (W3C ORG) for that snapshot |
| `Press-Release-*.md` | Source PSA press-release text (extracted from PDF) |
| `hierarchical_t0p005/` | **curated** per-class GeoJSON extracts + `classification_report.json` + `summary.md` |
| `enriched_t0p005/` | **intermediate** GeoJSON annotated with PSGC codes (`adm0`–`adm4`) |
| `raw_t0p005/` | **intermediate** NAMRIA shapefile → GeoJSON, before enrichment |

> The full pipeline and architecture are documented in [`AGENTS.md`](AGENTS.md).

## Snapshot history

17 quarterly snapshots are tracked, each producing an RDF delta against its predecessor:

`2021-08-19` · `2022-04-29` · `2022-11-08` · `2023-04-18` · `2023-08-15` · **`2023-10-24`** (first
fully enriched release) · `2024-01-23` · `2024-04-23` · `2024-05-08` · `2024-07-12` · `2024-10-18` ·
`2025-01-30` · `2025-04-23` · `2025-08-29` · `2025-10-13` · `2026-01-13` · `2026-04-13`.

Browse the full changelog →
[snapshot history](https://bendlikeabamboo.github.io/barangay-boundaries-repository/changelog/).

## Citation

If this dataset supports your work, please cite it. See [`CITATION.cff`](CITATION.cff) (or use
GitHub's **"Cite this repository"** button) and the
[citation page](https://bendlikeabamboo.github.io/barangay-boundaries-repository/citation/) for
ready-to-paste BibTeX and APA entries.

## License

Code is released under the **MIT License** — see [`LICENSE`](LICENSE).

### Data attribution

- **PSGC snapshots** — © Philippine Statistics Authority (PSA). Source:
  <https://psa.gov.ph/classification/psgc/>.
- **Administrative boundaries** — © NAMRIA, shapefile version `2023-11-06`. Source:
  <https://namria.gov.ph/>.

These datasets are redistributed for research and interoperability. Please credit PSA and NAMRIA in
any downstream product.

## Contributing

Issues and pull requests are welcome — especially PSGC/NAMRIA coverage gaps, new snapshot
processing, and HUC-mapping corrections. See [`AGENTS.md`](AGENTS.md) for the architecture and
conventions before contributing.
