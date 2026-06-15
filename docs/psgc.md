---
title: PSGC Code Structure — Philippine Standard Geographic Code
description: Reference for the 10-digit Philippine Standard Geographic Code (PSGC) hierarchy PPCCCMMLLL0, with region, province, municipality, and barangay examples.
---

# PSGC code structure

The **Philippine Standard Geographic Code (PSGC)** is a 10-digit hierarchical identifier
maintained by the [Philippine Statistics Authority (PSA)](https://psa.gov.ph/classification/psgc/).
Each administrative unit occupies a fixed segment of the code.

## The 10-digit hierarchy

Format: **`PPCCCMMLLL0`** (the final digit is a check/reserved position).

| Segment | Digits | Level | Example code | Example |
|---------|--------|-------|-------------|---------|
| Region | `PP` | ADM1 | `1300000000` | National Capital Region (NCR) |
| Province | `PPCCC` | ADM2 | `0139000000` | (province segment) |
| Municipality/City | `PPCCCMMLL` | ADM3 | `1376020000` | a municipality/city |
| Barangay | `PPCCCMMLLL` | ADM4 | `1376020068` | a barangay |

### Worked example

`1339060014` decodes as:

- `13` — NCR (region)
- `1339` — City of Makati (province-level / HUC)
- `133906` — City of Makati (municipality/city level)
- `1339060014` — a specific barangay within Makati

## Correspondence codes (9-digit identity)

A **9-digit correspondence code** tracks an entity's identity across PSGC code changes. When a
barangay is renamed, merged, split, or transferred, its 10-digit PSGC code may change but its
9-digit correspondence code stays stable. This repository uses correspondence codes to compute
deltas between snapshots.

## Code-change events detected

The RDF deltas (`delta.{ttl,nt,jsonld}`) classify changes into:

- `creation` — new entity
- `deletion` — removed entity
- `transfer` — moved between parents
- `renaming` — name change, same identity
- `merger` — two or more → one
- `split` — one → two or more
- `reclassification` — class change (e.g. municipality → city)
- `code_change` — identity preserved, code changed
- `reenlistment` — re-added after prior delisting

See [snapshot history](changelog.md) for the 17 processed quarters.
