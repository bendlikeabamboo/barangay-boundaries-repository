"""Integration test for the full hierarchical pipeline (plan §9.2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from barangay_boundaries_repository.splitter import OUTPUT_MAP


def _hierarchical_dir(repo_root: Path, snapshot_date: str) -> Path:
    return repo_root / snapshot_date / "hierarchical_t0p005"


@pytest.fixture(scope="module")
def report(repo_root: Path, snapshot_date: str) -> dict:
    d = _hierarchical_dir(repo_root, snapshot_date)
    path = d / "classification_report.json"
    if not path.exists():
        pytest.skip(
            "Run `brgybnd build-hierarchical --date 2023-10-24 "
            "--skip-convert --skip-enrich` first"
        )
    with open(path) as f:
        return json.load(f)


def test_all_output_files_exist(repo_root: Path, snapshot_date: str) -> None:
    d = _hierarchical_dir(repo_root, snapshot_date)
    for filename in OUTPUT_MAP.values():
        assert (d / f"{filename}.geojson").exists()
    assert (d / "unresolved.geojson").exists()
    assert (d / "classification_report.json").exists()


def test_expected_counts_within_tolerance(report: dict) -> None:
    rec = report["count_reconciliation"]
    # country tolerated (NAMRIA island polygons); submunicipality is a known
    # limitation. Everything else must reconcile.
    for ptype, info in rec.items():
        if ptype in ("country", "submunicipality"):
            continue
        assert info["ok"], f"{ptype}: {info}"


def test_conservation_ok(report: dict) -> None:
    assert report["validation"]["ok"], report["validation"]


def test_every_feature_has_matching_type(repo_root: Path, snapshot_date: str) -> None:
    d = _hierarchical_dir(repo_root, snapshot_date)
    for ptype, filename in OUTPUT_MAP.items():
        path = d / f"{filename}.geojson"
        with open(path) as f:
            data = json.load(f)
        for feature in data["features"]:
            props = feature["properties"]
            assert props["psgc_type"] == ptype, (
                f"{filename} contains feature with psgc_type={props['psgc_type']}"
            )


def test_huc_file_features_renested(repo_root: Path, snapshot_date: str) -> None:
    d = _hierarchical_dir(repo_root, snapshot_date)
    with open(d / "highly_urbanized_cities.geojson") as f:
        data = json.load(f)
    assert data["metadata"]["feature_count"] >= 33
    for feature in data["features"]:
        props = feature["properties"]
        assert props.get("province") is None
        assert props.get("namria_adm2_pcode"), "HUC must preserve namria_adm2_pcode"


def test_sga_barangays_flagged(repo_root: Path, snapshot_date: str) -> None:
    d = _hierarchical_dir(repo_root, snapshot_date)
    with open(d / "barangays.geojson") as f:
        data = json.load(f)
    sga = [f for f in data["features"] if f["properties"].get("sga_member")]
    assert len(sga) > 0, "expected SGA-member barangays to carry sga_member=true"
    for f in sga:
        assert f["properties"]["sga_member"] is True


def test_regional_counts(report: dict) -> None:
    per = report["per_type"]
    assert per["region"]["feature_count"] == 17
    assert per["province"]["feature_count"] == 82
    assert per["municipality"]["feature_count"] == 1485
    assert per["independent_component_city"]["feature_count"] == 6
