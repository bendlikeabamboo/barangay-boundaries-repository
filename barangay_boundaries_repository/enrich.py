from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import barangay as bg
import pandas as pd

from rapidfuzz.fuzz import token_set_ratio, token_sort_ratio

_MAPPING_PATH = Path(__file__).resolve().parent / "namria" / "huc_adm2_mapping.json"

_SANITIZE_TOKENS = {
    "(capital)",
    "(pob.)",
    "(pob)",
    "pob.",
    "(not a province)",
}


def _sanitize(name: str) -> str:
    n = name.lower().strip()
    for token in _SANITIZE_TOKENS:
        n = n.replace(token, "")
    n = re.sub(r"[\s()\-.,&]", " ", n)
    n = n.replace("city of ", "").replace("city", "").strip()
    return " ".join(n.split())


def _load_huc_mapping() -> dict:
    if not _MAPPING_PATH.exists():
        return {}
    with open(_MAPPING_PATH) as f:
        return json.load(f)


def enrich_geojson(
    geojson_path: Path,
    psgc_date: str,
    output_path: Path,
) -> dict:
    bg.use_version(psgc_date)

    huc_mapping = _load_huc_mapping()
    adm_level = _detect_adm_level(geojson_path)

    with open(geojson_path) as f:
        data = json.load(f)

    if adm_level == 0:
        return _enrich_adm0(data, output_path)
    elif adm_level == 1:
        return _enrich_adm1(data, psgc_date, output_path)
    elif adm_level == 2:
        return _enrich_adm2(data, huc_mapping, psgc_date, output_path)
    elif adm_level == 3:
        return _enrich_adm3(data, huc_mapping, psgc_date, output_path)
    elif adm_level == 4:
        return _enrich_adm4(data, huc_mapping, psgc_date, output_path)
    else:
        raise ValueError(f"Unknown ADM level: {adm_level}")


def _detect_adm_level(path: Path) -> int:
    name = path.stem
    for level in range(5):
        if name == f"adm{level}":
            return level
    raise ValueError(f"Cannot detect ADM level from filename: {path}")


def _enrich_adm0(data: dict, output_path: Path) -> dict:
    for feature in data["features"]:
        feature["properties"]["psgc_id"] = "PH"
        feature["properties"]["psgc_code"] = "0000000000"
        feature["properties"]["psgc_name"] = "Philippines (the)"
        feature["properties"]["psgc_status"] = "matched"
        feature["properties"]["match_confidence"] = 1.0

    return _write_output(data, output_path)


def _enrich_adm1(data: dict, psgc_date: str, output_path: Path) -> dict:
    bg.use_version(psgc_date)
    regions_df = bg.regions.to_frame()

    psgc_by_code: dict[str, tuple[str, str]] = {}
    for _, row in regions_df.iterrows():
        pcode = "PH" + str(row["psgc_id"])[:2]
        psgc_by_code[pcode] = (str(row["psgc_id"]), row.iloc[0])

    for feature in data["features"]:
        props = feature["properties"]
        pcode = props.get("ADM1_PCODE", "")

        if pcode in psgc_by_code:
            psgc_code, psgc_name = psgc_by_code[pcode]
            props["psgc_id"] = pcode
            props["psgc_code"] = psgc_code
            props["psgc_name"] = psgc_name
            props["psgc_status"] = "matched"
            props["match_confidence"] = 1.0
        else:
            props["psgc_status"] = "unmatched"

    return _write_output(data, output_path)


def _enrich_adm2(
    data: dict,
    huc_mapping: dict,
    psgc_date: str,
    output_path: Path,
) -> dict:
    bg.use_version(psgc_date)
    provinces_df = bg.provinces.to_frame()

    psgc_by_code: dict[str, tuple[str, str]] = {}
    for _, row in provinces_df.iterrows():
        pcode = "PH" + str(row["psgc_id"])[:5]
        psgc_by_code[pcode] = (str(row["psgc_id"]), row.iloc[0])

    virtual_provinces = huc_mapping.get("virtual_provinces", {})
    mm_districts = huc_mapping.get("metro_manila_districts", {})

    for feature in data["features"]:
        props = feature["properties"]
        pcode = props.get("ADM2_PCODE", "")

        if pcode in psgc_by_code:
            psgc_code, psgc_name = psgc_by_code[pcode]
            props["psgc_id"] = pcode
            props["psgc_code"] = psgc_code
            props["psgc_name"] = psgc_name
            props["psgc_status"] = "matched"
            props["match_confidence"] = 1.0
        elif pcode in virtual_provinces:
            vp = virtual_provinces[pcode]
            vp_type = vp.get("type", "")
            vp_psgc_code = vp.get("psgc_code")
            psgc_pcode = vp.get("psgc_pcode")

            if psgc_pcode:
                props["psgc_id"] = psgc_pcode
                props["psgc_code"] = vp_psgc_code
                props["psgc_name"] = vp.get("name", props.get("ADM2_EN", ""))
                props["psgc_status"] = "matched"
                props["match_confidence"] = 1.0
            elif vp_type == "mm_district":
                district_cities = mm_districts.get(pcode, [])
                all_city_names: list[str] = []
                for cpcode in district_cities:
                    adm3_pcode = "PH" + cpcode[2:]
                    if adm3_pcode in huc_mapping.get("namria_adm3_to_psgc", {}):
                        all_city_names.append(cpcode)
                props["psgc_id"] = None
                props["psgc_code"] = None
                props["psgc_name"] = vp.get("name", props.get("ADM2_EN", ""))
                props["psgc_status"] = "non-standard"
                props["match_confidence"] = None
                props["psgc_constituent_codes"] = district_cities
            else:
                props["psgc_status"] = "non-standard"
                props["match_confidence"] = None
        else:
            props["psgc_status"] = "unmatched"

    return _write_output(data, output_path)


def _enrich_adm3(
    data: dict,
    huc_mapping: dict,
    psgc_date: str,
    output_path: Path,
) -> dict:
    bg.use_version(psgc_date)
    munis_df = bg.municipalities.to_frame()
    cities_df = bg.cities.to_frame()

    adm3_dfs = [df for df in (munis_df, cities_df) if len(df) > 0]
    if not adm3_dfs:
        return _write_output(data, output_path)

    combined = pd.concat(adm3_dfs, ignore_index=True)
    psgc_by_pcode: dict[str, tuple[str, str]] = {}
    for _, row in combined.iterrows():
        pcode = "PH" + str(row["psgc_id"])[:7]
        psgc_by_pcode[pcode] = (str(row["psgc_id"]), row.iloc[0])

    adm3_to_psgc = huc_mapping.get("namria_adm3_to_psgc", {})
    psgc_sanitized: dict[str, str] = {k: _sanitize(v[1]) for k, v in psgc_by_pcode.items()}

    for feature in data["features"]:
        props = feature["properties"]
        namria_pcode = props.get("ADM3_PCODE", "")
        namria_name = props.get("ADM3_EN", "")

        if namria_pcode in adm3_to_psgc:
            psgc_pcode = adm3_to_psgc[namria_pcode]
            if psgc_pcode in psgc_by_pcode:
                psgc_id, psgc_name = psgc_by_pcode[psgc_pcode]
                props["psgc_id"] = psgc_pcode
                props["psgc_code"] = psgc_id
                props["psgc_name"] = psgc_name
                props["psgc_status"] = "matched"
                props["match_confidence"] = 1.0
            else:
                props["psgc_id"] = psgc_pcode
                props["psgc_code"] = None
                props["psgc_name"] = None
                props["psgc_status"] = "mapped-no-psgc"
                props["match_confidence"] = None
        elif namria_pcode in psgc_by_pcode:
            psgc_id, psgc_name = psgc_by_pcode[namria_pcode]
            props["psgc_id"] = namria_pcode
            props["psgc_code"] = psgc_id
            props["psgc_name"] = psgc_name
            props["psgc_status"] = "matched"
            props["match_confidence"] = 1.0
        else:
            gj_san = _sanitize(namria_name)
            best_psgc_pcode: str | None = None
            best_score = 0.0

            for psgc_pcode, psgc_san in psgc_sanitized.items():
                if psgc_pcode in adm3_to_psgc:
                    continue
                score = max(
                    token_set_ratio(gj_san, psgc_san),
                    token_sort_ratio(gj_san, psgc_san),
                )
                if score > best_score:
                    best_score = score
                    best_psgc_pcode = psgc_pcode

            if best_psgc_pcode and best_score >= 70:
                psgc_id, psgc_name = psgc_by_pcode[best_psgc_pcode]
                props["psgc_id"] = best_psgc_pcode
                props["psgc_code"] = psgc_id
                props["psgc_name"] = psgc_name
                props["psgc_status"] = "fuzzy"
                props["match_confidence"] = round(best_score / 100, 3)
            else:
                props["psgc_status"] = "unmatched"

    return _write_output(data, output_path)


def _enrich_adm4(
    data: dict,
    huc_mapping: dict,
    psgc_date: str,
    output_path: Path,
) -> dict:
    bg.use_version(psgc_date)
    barangays_df = bg.barangays.to_frame()
    sga_df = bg.special_geographic_areas.to_frame()

    adm4_dfs = [df for df in (barangays_df, sga_df) if len(df) > 0]
    if not adm4_dfs:
        return _write_output(data, output_path)

    combined = pd.concat(adm4_dfs, ignore_index=True)

    psgc_by_parent: dict[str, dict[str, tuple[str, str]]] = defaultdict(dict)
    psgc_by_code: dict[str, tuple[str, str]] = {}
    for _, row in combined.iterrows():
        psgc_id = str(row["psgc_id"])
        psgc_pcode = "PH" + psgc_id[:10]
        name = row.iloc[0]
        parent_pcode = "PH" + str(row["parent_psgc_id"])[:7]
        psgc_by_parent[parent_pcode][psgc_pcode] = (psgc_id, name)
        psgc_by_code[psgc_pcode] = (psgc_id, name)

    adm3_to_psgc = huc_mapping.get("namria_adm3_to_psgc", {})

    for feature in data["features"]:
        props = feature["properties"]
        namria_pcode = props.get("ADM4_PCODE", "")
        namria_name = props.get("ADM4_EN", "")
        namria_adm3_pcode = props.get("ADM3_PCODE", "")

        psgc_parent = namria_adm3_pcode

        if namria_adm3_pcode in adm3_to_psgc:
            psgc_parent = adm3_to_psgc[namria_adm3_pcode]

        psgc_brgys = psgc_by_parent.get(psgc_parent, {})

        if namria_pcode in psgc_brgys:
            brgy_psgc_id, brgy_name = psgc_brgys[namria_pcode]
            props["psgc_id"] = namria_pcode
            props["psgc_code"] = brgy_psgc_id
            props["psgc_name"] = brgy_name
            props["psgc_status"] = "matched"
            props["match_confidence"] = 1.0
        elif psgc_brgys:
            gj_san = _sanitize(namria_name)
            best_psgc: str | None = None
            best_score = 0.0

            for psgc_code, (brgy_psgc_id, psgc_name) in psgc_brgys.items():
                psgc_san = _sanitize(psgc_name)
                score = max(
                    token_set_ratio(gj_san, psgc_san),
                    token_sort_ratio(gj_san, psgc_san),
                )
                if score > best_score:
                    best_score = score
                    best_psgc = psgc_code

            if best_psgc and best_score >= 70:
                brgy_psgc_id, brgy_name = psgc_brgys[best_psgc]
                props["psgc_id"] = best_psgc
                props["psgc_code"] = brgy_psgc_id
                props["psgc_name"] = brgy_name
                props["psgc_status"] = "fuzzy"
                props["match_confidence"] = round(best_score / 100, 3)
            else:
                props["psgc_status"] = "unmatched"
        else:
            props["psgc_status"] = "unmatched"

    return _write_output(data, output_path)


def _write_output(data: dict, output_path: Path) -> dict:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data
