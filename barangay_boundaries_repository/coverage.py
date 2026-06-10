from __future__ import annotations

import json
import logging
from pathlib import Path

import barangay as bg
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_NAME_COL = "ADM{level}_EN"
_PCODE_COL = "ADM{level}_PCODE"

_ADM0_PCODE = "PH"

_MAPPING_PATH = Path(__file__).resolve().parent / "namria" / "huc_adm2_mapping.json"


def _load_huc_mapping() -> dict:
    if not _MAPPING_PATH.exists():
        return {}
    with open(_MAPPING_PATH) as f:
        return json.load(f)


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
    logger.info("Loading PSGC pcodes for %s...", date)
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
    sga_df = bg.special_geographic_areas.to_frame()
    if len(municipalities_df) > 0 or len(cities_df) > 0 or len(sga_df) > 0:
        adm3_dfs = [df for df in (municipalities_df, cities_df, sga_df) if len(df) > 0]
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

    logger.info(
        "PSGC pcodes by level: %s",
        {lvl: len(codes) for lvl, codes in sorted(result.items())},
    )

    return result


def load_psgc_pcodes_hierarchical(
    date: str,
) -> tuple[dict[int, dict[str, str]], dict[str, str]]:
    bg.use_version(date)

    huc_mapping = _load_huc_mapping()
    adm3_to_psgc = huc_mapping.get("namria_adm3_to_psgc", {})

    result: dict[int, dict[str, str]] = {}
    namria_psgc_adm3: dict[str, str] = {}

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

        for _, row in combined.iterrows():
            psgc_id = str(row["psgc_id"])
            psgc_pcode = "PH" + psgc_id[:7]
            name = row.iloc[0]

            if psgc_pcode in namria_psgc_adm3:
                continue

            parent_psgc_id = str(row["parent_psgc_id"])
            is_huc = parent_psgc_id.endswith("0000000")

            if is_huc and len(cities_df) > 0:
                huc_cities = cities_df[
                    cities_df["parent_psgc_id"] == row["parent_psgc_id"]
                ]
                if len(huc_cities) == 1:
                    huc_row = huc_cities.iloc[0]
                    huc_psgc_id = str(huc_row["psgc_id"])
                    huc_pcode = "PH" + huc_psgc_id[:7]
                    namria_psgc_adm3[huc_pcode] = name
                    continue

            namria_psgc_adm3[psgc_pcode] = name

    for namria_pcode, name in namria_psgc_adm3.items():
        if namria_pcode not in result.get(3, {}):
            if 3 not in result:
                result[3] = {}
            result[3][namria_pcode] = name

    barangays_df = bg.barangays.to_frame()
    sga_df = bg.special_geographic_areas.to_frame()
    if len(barangays_df) > 0 or len(sga_df) > 0:
        adm4_dfs = [df for df in (barangays_df, sga_df) if len(df) > 0]
        combined = pd.concat(adm4_dfs, ignore_index=True)

        namria_psgc_adm4: dict[str, str] = {}
        for _, row in combined.iterrows():
            psgc_id = str(row["psgc_id"])
            name = row.iloc[0]
            parent_psgc_id = str(row["parent_psgc_id"])
            parent_pcode = "PH" + parent_psgc_id[:7]

            if parent_pcode in adm3_to_psgc:
                namria_parent = adm3_to_psgc[parent_pcode]
            elif parent_pcode in namria_psgc_adm3:
                namria_parent = parent_pcode
            else:
                namria_parent = parent_pcode

            namria_pcode = namria_parent + psgc_id[7:10]
            namria_psgc_adm4[namria_pcode] = name

        result[4] = namria_psgc_adm4

    result[0] = {_ADM0_PCODE: "Philippines (the)"}

    return result, adm3_to_psgc


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

            pcode = props.get("psgc_id")
            if pcode is None:
                pcode = props.get(_PCODE_COL.format(level=adm_level))

            name = props.get("psgc_name") or props.get(
                _NAME_COL.format(level=adm_level), ""
            )

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
    *,
    enriched_geojson_dir: Path | None = None,
) -> CoverageReport:
    report = CoverageReport(date="")

    all_levels = sorted(set(list(psgc.keys()) + list(geojson.keys())))

    for adm_level in all_levels:
        psgc_map = psgc.get(adm_level, {})
        geojson_map = geojson.get(adm_level, {})

        psgc_set = set(psgc_map.keys())
        geojson_set = set(geojson_map.keys())

        matched = psgc_set & geojson_set

        if enriched_geojson_dir is not None:
            enriched_path = enriched_geojson_dir / f"adm{adm_level}.geojson"
            if enriched_path.exists():
                enriched_psgc_ids: set[str] = set()
                with open(enriched_path) as f:
                    enriched_data = json.load(f)
                for feature in enriched_data["features"]:
                    psgc_id = feature.get("properties", {}).get("psgc_id")
                    status = feature.get("properties", {}).get("psgc_status", "")
                    if psgc_id and status in ("matched", "fuzzy"):
                        enriched_psgc_ids.add(psgc_id)
                enriched_matched = enriched_psgc_ids & psgc_set
                matched = matched | enriched_matched

        report.levels[adm_level] = LevelResult(
            adm_level=adm_level,
            psgc_count=len(psgc_set),
            geojson_count=len(geojson_set),
            matched_count=len(matched),
            matched_pcodes=matched,
            psgc_only={k: psgc_map[k] for k in sorted(psgc_set - geojson_set)},
            geojson_only={k: geojson_map[k] for k in sorted(geojson_set - matched)},
        )

    return report


def compute_coverage_with_huc(
    psgc: dict[int, dict[str, str]],
    geojson: dict[int, dict[str, str]],
    *,
    enriched_geojson_dir: Path | None = None,
) -> CoverageReport:
    huc_mapping = _load_huc_mapping()
    virtual_provinces = huc_mapping.get("virtual_provinces", {})

    report = compute_coverage(psgc, geojson, enriched_geojson_dir=enriched_geojson_dir)

    adm2 = report.levels.get(2)
    if adm2 is None:
        return report

    extra_matched: set[str] = set()
    vp_pcodes: set[str] = set()

    for _namria_code, vp_info in virtual_provinces.items():
        vp_pcode = vp_info.get("psgc_pcode")
        if vp_pcode:
            vp_pcodes.add(vp_pcode)

    for gj_code in list(adm2.geojson_only.keys()):
        if gj_code in virtual_provinces or gj_code in vp_pcodes:
            extra_matched.add(gj_code)

    if extra_matched:
        adm2.matched_count += len(extra_matched)
        adm2.matched_pcodes = adm2.matched_pcodes | extra_matched
        adm2.geojson_only = {
            k: v for k, v in adm2.geojson_only.items() if k not in extra_matched
        }

    return report
