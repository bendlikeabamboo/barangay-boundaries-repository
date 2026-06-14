"""Unit tests for the splitter (plan §9.3)."""

from __future__ import annotations

import json

from barangay_boundaries_repository.splitter import (
    OUTPUT_MAP,
    bucket_features,
    validate_conservation,
    write_hierarchical,
)


def _feature(ptype: str, method: str = "exact", **extra) -> dict:
    props = {"psgc_type": ptype, "match_method": method}
    props.update(extra)
    return {"type": "Feature", "properties": props, "geometry": None}


def test_bucketing_routes_known_types() -> None:
    classified = {
        0: {"features": [_feature("country")]},
        1: {"features": [_feature("region"), _feature("region")]},
        3: {
            "features": [
                _feature("municipality"),
                _feature("highly_urbanized_city"),
                _feature("component_city"),
            ]
        },
    }
    buckets = bucket_features(classified)
    assert len(buckets["country"]) == 1
    assert len(buckets["region"]) == 2
    assert len(buckets["municipality"]) == 1
    assert len(buckets["highly_urbanized_city"]) == 1
    assert len(buckets["component_city"]) == 1


def test_bucketing_routes_virtual_to_unresolved() -> None:
    classified = {
        2: {"features": [_feature("mm_district", "huc_map")]},
        3: {"features": [_feature("huc_isabela", "huc_map")]},
    }
    buckets = bucket_features(classified)
    assert "unresolved" in buckets
    assert len(buckets["unresolved"]) == 2


def test_bucketing_routes_non_admin_separately() -> None:
    classified = {
        4: {"features": [_feature("non_administrative", "non_administrative")]}
    }
    buckets = bucket_features(classified)
    assert len(buckets["non_administrative"]) == 1
    assert "unresolved" not in buckets or len(buckets["unresolved"]) == 0


def test_write_hierarchical_metadata(tmp_path) -> None:
    classified = {
        1: {"features": [_feature("region"), _feature("region")]},
        3: {"features": [_feature("municipality", "exact")]},
    }
    buckets = bucket_features(classified)
    report = write_hierarchical(
        buckets,
        tmp_path,
        psgc_version="2023-10-24",
        namria_version="2023-11-06",
    )
    regions_path = tmp_path / "regions.geojson"
    assert regions_path.exists()
    with open(regions_path) as f:
        data = json.load(f)
    assert data["metadata"]["psgc_type"] == "region"
    assert data["metadata"]["feature_count"] == 2
    assert data["metadata"]["match_summary"]["exact"] == 2
    assert report["total_written"] == 3
    assert (tmp_path / "classification_report.json").exists()


def test_write_hierarchical_empty_buckets(tmp_path) -> None:
    buckets = {}
    report = write_hierarchical(
        buckets,
        tmp_path,
        psgc_version="2023-10-24",
        namria_version="2023-11-06",
    )
    # Every OUTPUT_MAP file is still emitted (empty)
    for ptype, filename in OUTPUT_MAP.items():
        assert (tmp_path / f"{filename}.geojson").exists()
    assert report["total_written"] == 0


def test_write_hierarchical_submuni_limitation(tmp_path) -> None:
    buckets = {}
    report = write_hierarchical(
        buckets,
        tmp_path,
        psgc_version="2023-10-24",
        namria_version="2023-11-06",
    )
    assert "submunicipalities" in report["limitations"]
    assert len(report["limitations"]["submunicipalities"]["expected_pcodes"]) == 14


def test_validate_conservation_ok() -> None:
    report = {"total_written": 5}
    assert validate_conservation({1: 2, 3: 3}, report) == []


def test_validate_conservation_fail() -> None:
    report = {"total_written": 4}
    errors = validate_conservation({1: 2, 3: 3}, report)
    assert len(errors) == 1
