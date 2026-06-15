---
title: Snapshot History — PSGC Change Changelog
description: Quarterly Philippine Standard Geographic Code (PSGC) change history across 17 snapshots from 2021-08-19 to 2026-04-13, published as RDF deltas.
---

# PSGC snapshot history

This dataset tracks **17 quarterly PSGC snapshots**. Each snapshot is processed into an RDF delta
(`delta.ttl` / `.nt` / `.jsonld`) capturing creation, deletion, transfer, merger, split, renaming,
reclassification, and code-change events relative to the previous snapshot.

| # | Snapshot | Notes |
|--:|----------|-------|
| 1 | `2021-08-19` | Baseline |
| 2 | `2022-04-29` | Largest delta of the series |
| 3 | `2022-11-08` | |
| 4 | `2023-04-18` | |
| 5 | `2023-08-15` | 2Q 2023 |
| 6 | **`2023-10-24`** | **First fully enriched release (3Q 2023)** — GeoJSON bundles published |
| 7 | `2024-01-23` | No change in 4Q 2023 |
| 8 | `2024-04-23` | |
| 9 | `2024-05-08` | Eight new municipalities in BARMM |
| 10 | `2024-07-12` | June 2024 PSGC |
| 11 | `2024-10-18` | 3Q 2024 |
| 12 | `2025-01-30` | |
| 13 | `2025-04-23` | 1Q 2025 |
| 14 | `2025-08-29` | July 2025 PSGC |
| 15 | `2025-10-13` | 3Q 2025 |
| 16 | `2026-01-13` | 4Q 2025 |
| 17 | `2026-04-13` | 1Q 2026 |

## Reading the deltas

Each snapshot directory in the repository contains `delta.ttl` (Turtle), `delta.nt` (N-Triples),
and `delta.jsonld` (JSON-LD), plus the source PSA press release as Markdown. The RDF uses the
[W3C ORG ontology](https://www.w3.org/TR/vocab-org/) with PROV provenance and Dublin Core terms.

## Releases

Tagged releases follow the pattern `vYYYY-MM-DD`, one per processed snapshot. See
[Releases](https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases). The inaugural
data release is **[`v2023-10-24`](https://github.com/bendlikeabamboo/barangay-boundaries-repository/releases/tag/v2023-10-24)**.
