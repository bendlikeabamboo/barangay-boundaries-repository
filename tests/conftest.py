"""Shared pytest fixtures for the hierarchical pipeline tests."""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATE = "2023-10-24"


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return _REPO_ROOT


@pytest.fixture(scope="session")
def snapshot_date() -> str:
    return DEFAULT_DATE


@pytest.fixture(scope="session")
def enriched_dir(repo_root: Path, snapshot_date: str) -> Path:
    d = repo_root / snapshot_date / "enriched_t0p005"
    if not d.exists():
        pytest.skip(f"Enriched fixtures missing: {d}")
    return d


def load_geojson(path: Path) -> dict:
    import json

    with open(path) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def enriched_adm3(enriched_dir: Path) -> dict:
    return load_geojson(enriched_dir / "adm3.geojson")


@pytest.fixture(scope="session")
def enriched_adm2(enriched_dir: Path) -> dict:
    return load_geojson(enriched_dir / "adm2.geojson")


@pytest.fixture(scope="session")
def enriched_adm4(enriched_dir: Path) -> dict:
    return load_geojson(enriched_dir / "adm4.geojson")


def find_feature(data: dict, **kwargs) -> dict:
    """Return the first feature whose properties match all kwargs."""
    for feature in data["features"]:
        props = feature.get("properties", {})
        if all(str(props.get(k)) == str(v) for k, v in kwargs.items()):
            return feature
    raise AssertionError(f"No feature matching {kwargs}")
