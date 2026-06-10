from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from pathlib import Path

import barangay as bg
import pandas as pd

from rapidfuzz.fuzz import token_set_ratio, token_sort_ratio

logger = logging.getLogger(__name__)

_MAPPING_PATH = Path(__file__).resolve().parent / "namria" / "huc_adm2_mapping.json"

_SANITIZE_TOKENS = {
    "(capital)",
    "(pob.)",
    "(pob)",
    "pob.",
    "(not a province)",
}

_NON_ADMIN_PATTERNS = [
    "forest land",
    "timber land",
    "mount apo",
    "watershed",
    "unclaimed area",
    "national park",
    "cemetery",
    "mall (claimed",
]


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
    logger.info("Enriching %s with PSGC data from %s", geojson_path.name, psgc_date)
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
    logger.info(
        "  ADM2 enrichment: matching %d features against PSGC provinces",
        len(data["features"]),
    )
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
    logger.info(
        "  ADM3 enrichment: matching %d features against PSGC municipalities/cities",
        len(data["features"]),
    )
    bg.use_version(psgc_date)
    munis_df = bg.municipalities.to_frame()
    cities_df = bg.cities.to_frame()
    sga_df = bg.special_geographic_areas.to_frame()

    adm3_dfs = [df for df in (munis_df, cities_df, sga_df) if len(df) > 0]
    if not adm3_dfs:
        return _write_output(data, output_path)

    combined = pd.concat(adm3_dfs, ignore_index=True)
    psgc_by_pcode: dict[str, tuple[str, str]] = {}
    for _, row in combined.iterrows():
        pcode = "PH" + str(row["psgc_id"])[:7]
        psgc_by_pcode[pcode] = (str(row["psgc_id"]), row.iloc[0])

    adm3_to_psgc = huc_mapping.get("namria_adm3_to_psgc", {})
    psgc_sanitized: dict[str, str] = {
        k: _sanitize(v[1]) for k, v in psgc_by_pcode.items()
    }

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
    logger.info(
        "  ADM4 enrichment: matching %d barangay features (this may take a while)",
        len(data["features"]),
    )
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

    submuni_parents = huc_mapping.get("submunicipality_parents", {})
    cross_parent_map = huc_mapping.get("cross_parent_mapping", {})
    adm3_to_psgc = huc_mapping.get("namria_adm3_to_psgc", {})

    def _resolve_parent_brgys(psgc_parent: str) -> dict[str, tuple[str, str]]:
        brgys: dict[str, tuple[str, str]] = {}
        brgys.update(psgc_by_parent.get(psgc_parent, {}))
        for submuni_pcode in submuni_parents.get(psgc_parent, []):
            brgys.update(psgc_by_parent.get(submuni_pcode, {}))
        return brgys

    def _try_match(
        psgc_brgys: dict[str, tuple[str, str]],
        namria_pcode: str,
        namria_name: str,
    ) -> tuple[bool, str | None, str | None, str | None]:
        if namria_pcode in psgc_brgys:
            brgy_psgc_id, brgy_name = psgc_brgys[namria_pcode]
            return True, namria_pcode, brgy_psgc_id, brgy_name
        if psgc_brgys:
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
                return True, best_psgc, brgy_psgc_id, brgy_name
        return False, None, None, None

    for feature in data["features"]:
        props = feature["properties"]
        namria_pcode = props.get("ADM4_PCODE", "")
        namria_name = props.get("ADM4_EN", "")
        namria_adm3_pcode = props.get("ADM3_PCODE", "")

        name_lower = namria_name.lower().strip()
        if any(pat in name_lower for pat in _NON_ADMIN_PATTERNS):
            props["psgc_id"] = None
            props["psgc_code"] = None
            props["psgc_name"] = None
            props["psgc_status"] = "non-administrative"
            props["match_confidence"] = None
            continue

        psgc_parent = namria_adm3_pcode

        if namria_adm3_pcode in adm3_to_psgc:
            psgc_parent = adm3_to_psgc[namria_adm3_pcode]

        psgc_brgys = _resolve_parent_brgys(psgc_parent)

        matched, match_id, match_code, match_name = _try_match(
            psgc_brgys, namria_pcode, namria_name
        )

        if not matched:
            for alt_parent in cross_parent_map.get(psgc_parent, []):
                alt_brgys = _resolve_parent_brgys(alt_parent)
                matched, match_id, match_code, match_name = _try_match(
                    alt_brgys, namria_pcode, namria_name
                )
                if matched:
                    break

        if matched and match_id and match_code is not None and match_name is not None:
            props["psgc_id"] = match_id
            props["psgc_code"] = match_code
            props["psgc_name"] = match_name
            if match_id == namria_pcode:
                props["psgc_status"] = "matched"
                props["match_confidence"] = 1.0
            else:
                props["psgc_status"] = "fuzzy"
                gj_san = _sanitize(namria_name)
                psgc_san = _sanitize(match_name)
                score = max(
                    token_set_ratio(gj_san, psgc_san),
                    token_sort_ratio(gj_san, psgc_san),
                )
                props["match_confidence"] = round(score / 100, 3)
        else:
            props["psgc_status"] = "unmatched"

    unmatched_features = [
        f for f in data["features"] if f["properties"].get("psgc_status") == "unmatched"
    ]
    if unmatched_features and psgc_by_code:
        fallback_matches = _fallback_search_batch(
            unmatched_features, psgc_by_code, psgc_date
        )
        for gj_code, (
            psgc_id,
            psgc_code,
            psgc_name,
            confidence,
        ) in fallback_matches.items():
            for f in data["features"]:
                p = f["properties"]
                if p.get("ADM4_PCODE") == gj_code:
                    p["psgc_id"] = psgc_id
                    p["psgc_code"] = psgc_code
                    p["psgc_name"] = psgc_name
                    if confidence >= 1.0:
                        p["psgc_status"] = "matched"
                    else:
                        p["psgc_status"] = "fuzzy"
                    p["match_confidence"] = confidence
                    break

    return _write_output(data, output_path)


_SGA_ADM3_PREFIX = "Special Geographic Area - "

_SGA_EXCEPTION_DATE = "2023-10-24"

_HOOK_PASSES = [
    ["barangay", "municipality", "province"],
    ["barangay", "municipality"],
    ["barangay", "province"],
    ["barangay"],
]

_EXACT_NAME_HOOK_THRESHOLD = 100.0


def _compose_query(
    brgy_name: str,
    mun_name: str,
    prov_name: str,
    hooks: list[str],
    psgc_date: str,
) -> str:
    parts = [brgy_name]
    if "municipality" in hooks and mun_name:
        clean_mun = mun_name
        if psgc_date == _SGA_EXCEPTION_DATE and mun_name.startswith(_SGA_ADM3_PREFIX):
            clean_mun = mun_name[len(_SGA_ADM3_PREFIX) :]
        parts.append(clean_mun)
    if "province" in hooks and prov_name:
        parts.append(prov_name)
    return ", ".join(parts)


def _fallback_search_batch(
    unmatched_features: list[dict],
    all_psgc_brgys: dict[str, tuple[str, str]],
    psgc_date: str,
) -> dict[str, tuple[str, str, str, float]]:
    from barangay.models import AdminLevel
    from barangay.search import search_fuzzy

    remaining: dict[str, tuple[str, str, str]] = {}
    for feature in unmatched_features:
        p = feature["properties"]
        remaining[p["ADM4_PCODE"]] = (
            p.get("ADM4_EN", ""),
            p.get("ADM3_EN", ""),
            p.get("ADM2_EN", ""),
        )

    matched: dict[str, tuple[str, str, str, float]] = {}
    used_psgc: set[str] = set()

    for hooks in _HOOK_PASSES:
        if not remaining:
            break
        threshold = _EXACT_NAME_HOOK_THRESHOLD if hooks == ["barangay"] else 70.0
        for gj_code in list(remaining.keys()):
            brgy_name, mun_name, prov_name = remaining[gj_code]
            query = _compose_query(brgy_name, mun_name, prov_name, hooks, psgc_date)
            results = search_fuzzy(
                query,
                level=AdminLevel.BARANGAY,
                match_hooks=hooks,
                threshold=threshold,
                limit=1,
                as_of=psgc_date,
            )
            if results:
                r = results[0]
                psgc_pcode = "PH" + r.psgc_id
                if psgc_pcode in all_psgc_brgys and psgc_pcode not in used_psgc:
                    used_psgc.add(psgc_pcode)
                    brgy_psgc_id, brgy_name = all_psgc_brgys[psgc_pcode]
                    matched[gj_code] = (
                        psgc_pcode,
                        brgy_psgc_id,
                        brgy_name,
                        round(r.score / 100, 3),
                    )
                    del remaining[gj_code]

    return matched


def _write_output(data: dict, output_path: Path) -> dict:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    status_counts: dict[str, int] = {}
    for feature in data.get("features", []):
        status = feature.get("properties", {}).get("psgc_status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

    logger.info(
        "  Enrichment result → %s: %s",
        output_path.name,
        dict(sorted(status_counts.items())),
    )

    with open(output_path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data
