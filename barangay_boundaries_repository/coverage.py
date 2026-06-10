from __future__ import annotations

import json
from pathlib import Path

import barangay as bg
import pandas as pd
from pydantic import BaseModel, Field

_NAME_COL = "ADM{level}_EN"
_PCODE_COL = "ADM{level}_PCODE"

_ADM0_PCODE = "PH"


class LevelResult(BaseModel):
    adm_level: int
    psgc_count: int
    geojson_count: int
    matched_count: int
    matched_pcodes: set[str] = Field(default_factory=set)
    psgc_only: dict[str, str] = Field(default_factory=dict)
    geojson_only: dict[str, str] = Field(default_factory=dict)

    @property
    def coverage_pct(self) -> float:
        if self.geojson_count == 0:
            return 0.0
        return self.matched_count / self.geojson_count * 100


class CoverageReport(BaseModel):
    date: str
    levels: dict[int, LevelResult] = Field(default_factory=dict)

    @property
    def total_psgc(self) -> int:
        return sum(v.psgc_count for v in self.levels.values())

    @property
    def total_geojson(self) -> int:
        return sum(v.geojson_count for v in self.levels.values())

    @property
    def total_matched(self) -> int:
        return sum(v.matched_count for v in self.levels.values())

    @property
    def overall_coverage(self) -> float:
        if self.total_geojson == 0:
            return 0.0
        return self.total_matched / self.total_geojson * 100


def load_psgc_pcodes(date: str) -> dict[int, dict[str, str]]:
    bg.use_version(date)

    result: dict[int, dict[str, str]] = {}

    regions_df = bg.regions.to_frame()
    if len(regions_df) > 0:
        pcodes = "PH" + regions_df["psgc_id"].str[:2]
        result[1] = dict(zip(pcodes, regions_df["name"]))

    provinces_df = bg.provinces.to_frame()
    if len(provinces_df) > 0:
        pcodes = "PH" + provinces_df["psgc_id"].str[:5]
        result[2] = dict(zip(pcodes, provinces_df["name"]))

    municipalities_df = bg.municipalities.to_frame()
    cities_df = bg.cities.to_frame()
    if len(municipalities_df) > 0 or len(cities_df) > 0:
        adm3_dfs = [df for df in (municipalities_df, cities_df) if len(df) > 0]
        combined = pd.concat(adm3_dfs, ignore_index=True)
        pcodes = "PH" + combined["psgc_id"].str[:7]
        result[3] = dict(zip(pcodes, combined["name"]))

    barangays_df = bg.barangays.to_frame()
    sga_df = bg.special_geographic_areas.to_frame()
    if len(barangays_df) > 0 or len(sga_df) > 0:
        adm4_dfs = [df for df in (barangays_df, sga_df) if len(df) > 0]
        combined = pd.concat(adm4_dfs, ignore_index=True)
        pcodes = "PH" + combined["psgc_id"].str[:10]
        result[4] = dict(zip(pcodes, combined["name"]))

    result[0] = {_ADM0_PCODE: "Philippines (the)"}

    return result


def load_geojson_pcodes(geojson_dir: Path) -> dict[int, dict[str, str]]:
    result: dict[int, dict[str, str]] = {}

    for adm_level in range(5):
        geojson_path = geojson_dir / f"adm{adm_level}.geojson"
        if not geojson_path.exists():
            continue

        with open(geojson_path) as f:
            data = json.load(f)

        pcodes: dict[str, str] = {}
        for feature in data["features"]:
            props = feature.get("properties", {})
            pcode = props.get(_PCODE_COL.format(level=adm_level))
            name = props.get(_NAME_COL.format(level=adm_level), "")

            if adm_level == 0:
                pcode = _ADM0_PCODE
                name = name or "Philippines (the)"

            if pcode and pcode not in pcodes:
                pcodes[pcode] = name

        if pcodes:
            result[adm_level] = pcodes

    return result


def compute_coverage(
    psgc: dict[int, dict[str, str]],
    geojson: dict[int, dict[str, str]],
) -> CoverageReport:
    report = CoverageReport(date="")

    all_levels = sorted(set(list(psgc.keys()) + list(geojson.keys())))

    for adm_level in all_levels:
        psgc_map = psgc.get(adm_level, {})
        geojson_map = geojson.get(adm_level, {})

        psgc_set = set(psgc_map.keys())
        geojson_set = set(geojson_map.keys())

        matched = psgc_set & geojson_set

        report.levels[adm_level] = LevelResult(
            adm_level=adm_level,
            psgc_count=len(psgc_set),
            geojson_count=len(geojson_set),
            matched_count=len(matched),
            matched_pcodes=matched,
            psgc_only={k: psgc_map[k] for k in sorted(psgc_set - geojson_set)},
            geojson_only={k: geojson_map[k] for k in sorted(geojson_set - psgc_set)},
        )

    return report
