from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel

from rapidfuzz.fuzz import token_set_ratio, token_sort_ratio

logger = logging.getLogger(__name__)

_MAPPING_PATH = Path(__file__).resolve().parent / "namria" / "huc_adm2_mapping.json"


def _load_huc_mapping() -> dict:
    if not _MAPPING_PATH.exists():
        return {}
    with open(_MAPPING_PATH) as f:
        return json.load(f)


class ADM3Match(BaseModel):
    psgc_code: str
    psgc_name: str
    geojson_code: str
    geojson_name: str
    score: float


class ReconcileResult(BaseModel):
    date: str
    matches: list[ADM3Match]
    unresolved_psgc: dict[str, str]
    unresolved_geojson: dict[str, str]
    adm2_exclusions: dict[str, str]
    adm4_remapped: dict[str, str]
    adm4_unmatched_psgc: dict[str, str]
    adm4_unmatched_geojson: dict[str, str]


_ADM2_EXCLUSION_CODES = frozenset(
    {
        "PH09097",
        "PH13039",
        "PH13074",
        "PH13075",
        "PH13076",
        "PH19099",
    }
)

_NUMBERED_BARANGAY_RE = re.compile(r"^barangay\s+(\d+)", re.IGNORECASE)

_SANITIZERS = {
    "(pob.)",
    "(pob)",
    "pob.",
    "(capital)",
    "capital",
}


def _sanitize(name: str) -> str:
    n = name.lower().strip()
    for token in _SANITIZERS:
        n = n.replace(token, "")
    n = re.sub(r"[\s()\-.,&]", " ", n)
    return " ".join(n.split())


def _extract_barangay_number(name: str) -> str | None:
    m = _NUMBERED_BARANGAY_RE.match(name.strip())
    return m.group(1) if m else None


def _match_adm3(
    psgc_only: dict[str, str],
    geojson_only: dict[str, str],
    threshold: float,
    huc_mapping: dict | None = None,
) -> tuple[list[ADM3Match], dict[str, str], dict[str, str]]:
    logger.info(
        "ADM3 matching: %d PSGC-only, %d GeoJSON-only, threshold=%.0f",
        len(psgc_only),
        len(geojson_only),
        threshold * 100,
    )

    psgc_remaining = dict(psgc_only)
    gj_remaining = dict(geojson_only)
    matches: list[ADM3Match] = []

    adm3_to_psgc = {}
    if huc_mapping:
        adm3_to_psgc = huc_mapping.get("namria_adm3_to_psgc", {})

    direct_huc_matches: list[ADM3Match] = []
    if adm3_to_psgc:
        logger.debug("Applying %d HUC ADM3→PSGC mappings", len(adm3_to_psgc))
        for gj_code, gj_name in sorted(gj_remaining.items()):
            if gj_code in adm3_to_psgc:
                psgc_pcode = adm3_to_psgc[gj_code]
                if psgc_pcode in psgc_remaining:
                    direct_huc_matches.append(
                        ADM3Match(
                            psgc_code=psgc_pcode,
                            psgc_name=psgc_remaining[psgc_pcode],
                            geojson_code=gj_code,
                            geojson_name=gj_name,
                            score=1.0,
                        )
                    )
                    del psgc_remaining[psgc_pcode]
                    del gj_remaining[gj_code]

    logger.info(
        "  HUC direct matches: %d; remaining %d PSGC, %d GeoJSON for fuzzy matching",
        len(direct_huc_matches),
        len(psgc_remaining),
        len(gj_remaining),
    )

    psgc_sanitized = {k: _sanitize(v) for k, v in psgc_remaining.items()}
    gj_sanitized = {k: _sanitize(v) for k, v in gj_remaining.items()}

    for gj_code, gj_name in sorted(gj_remaining.items()):
        gj_san = gj_sanitized[gj_code]
        best_score = 0.0
        best_psgc_code: str | None = None

        for psgc_code, psgc_name in psgc_remaining.items():
            psgc_san = psgc_sanitized[psgc_code]

            set_score = token_set_ratio(gj_san, psgc_san)
            sort_score = token_sort_ratio(gj_san, psgc_san)
            score = max(set_score, sort_score)

            if score > best_score:
                best_score = score
                best_psgc_code = psgc_code

        if best_psgc_code and best_score >= threshold * 100:
            matches.append(
                ADM3Match(
                    psgc_code=best_psgc_code,
                    psgc_name=psgc_remaining[best_psgc_code],
                    geojson_code=gj_code,
                    geojson_name=gj_name,
                    score=best_score / 100,
                )
            )
            del psgc_remaining[best_psgc_code]
            del gj_remaining[gj_code]

    all_matches = direct_huc_matches + matches
    return all_matches, psgc_remaining, gj_remaining


def _match_adm4_by_parent(
    adm3_matches: list[ADM3Match],
    psgc_only_adm4: dict[str, str],
    geojson_only_adm4: dict[str, str],
    huc_mapping: dict | None = None,
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    logger.info(
        "ADM4 by-parent matching: %d PSGC-only barangays, %d GeoJSON-only barangays, %d ADM3 matches as parent keys",
        len(psgc_only_adm4),
        len(geojson_only_adm4),
        len(adm3_matches),
    )

    adm3_to_psgc = {}
    if huc_mapping:
        adm3_to_psgc = huc_mapping.get("namria_adm3_to_psgc", {})

    gj_psgc_parent_map: dict[str, str] = {}
    for match in adm3_matches:
        gj_psgc_parent_map[match.geojson_code] = match.psgc_code

    gj_parent_groups: dict[str, dict[str, str]] = defaultdict(dict)
    for code, name in geojson_only_adm4.items():
        namria_parent = code[:9]
        psgc_parent = gj_psgc_parent_map.get(namria_parent, namria_parent)
        gj_parent_groups[psgc_parent][code] = name

    psgc_parent_groups: dict[str, dict[str, str]] = defaultdict(dict)
    for code, name in psgc_only_adm4.items():
        psgc_parent_prefix = code[:9]
        mapped_parent = adm3_to_psgc.get(psgc_parent_prefix, psgc_parent_prefix)
        psgc_parent_groups[mapped_parent][code] = name

    remapped: dict[str, str] = {}
    unmatched_psgc: dict[str, str] = dict(psgc_only_adm4)
    unmatched_gj: dict[str, str] = dict(geojson_only_adm4)

    all_parents = set(gj_parent_groups.keys()) | set(psgc_parent_groups.keys())

    for parent in all_parents:
        psgc_brgys = psgc_parent_groups.get(parent, {})
        gj_brgys = gj_parent_groups.get(parent, {})
        if not psgc_brgys or not gj_brgys:
            continue

        psgc_by_san: dict[str, list[str]] = defaultdict(list)
        psgc_by_num: dict[str, list[str]] = defaultdict(list)
        for code, name in psgc_brgys.items():
            san = _sanitize(name)
            psgc_by_san[san].append(code)
            num = _extract_barangay_number(name)
            if num:
                psgc_by_num[num].append(code)

        gj_matched: set[str] = set()
        psgc_matched: set[str] = set()

        for gj_code, gj_name in gj_brgys.items():
            if gj_code in gj_matched:
                continue
            gj_san = _sanitize(gj_name)
            gj_num = _extract_barangay_number(gj_name)

            if gj_num and gj_num in psgc_by_num:
                candidates = psgc_by_num[gj_num]
                matched = False
                for psgc_code in candidates:
                    if psgc_code not in psgc_matched:
                        remapped[gj_code] = psgc_code
                        gj_matched.add(gj_code)
                        psgc_matched.add(psgc_code)
                        unmatched_gj.pop(gj_code, None)
                        unmatched_psgc.pop(psgc_code, None)
                        matched = True
                        break
                if matched:
                    continue

            if gj_san in psgc_by_san:
                candidates = psgc_by_san[gj_san]
                matched = False
                for psgc_code in candidates:
                    if psgc_code not in psgc_matched:
                        remapped[gj_code] = psgc_code
                        gj_matched.add(gj_code)
                        psgc_matched.add(psgc_code)
                        unmatched_gj.pop(gj_code, None)
                        unmatched_psgc.pop(psgc_code, None)
                        matched = True
                        break
                if matched:
                    continue

            best_score = 0.0
            best_psgc: str | None = None
            for psgc_code, psgc_name in psgc_brgys.items():
                if psgc_code in psgc_matched:
                    continue
                psgc_san = _sanitize(psgc_name)
                score = max(
                    token_set_ratio(gj_san, psgc_san),
                    token_sort_ratio(gj_san, psgc_san),
                )
                if score > best_score:
                    best_score = score
                    best_psgc = psgc_code

            if best_psgc and best_score >= 90:
                remapped[gj_code] = best_psgc
                gj_matched.add(gj_code)
                psgc_matched.add(best_psgc)
                unmatched_gj.pop(gj_code, None)
                unmatched_psgc.pop(best_psgc, None)

    logger.info(
        "ADM4 by-parent result: %d remapped, %d unmatched PSGC, %d unmatched GeoJSON",
        len(remapped),
        len(unmatched_psgc),
        len(unmatched_gj),
    )

    return remapped, unmatched_psgc, unmatched_gj


def reconcile(
    diff_path: Path,
    threshold: float = 0.7,
    as_of: str | None = None,
) -> ReconcileResult:
    logger.info("Reconciling from %s (threshold=%.2f)", diff_path, threshold)
    huc_mapping = _load_huc_mapping()

    with open(diff_path) as f:
        diff = json.load(f)

    date = diff["date"]
    adm2_data = diff["levels"].get("ADM2", {})
    adm3_data = diff["levels"].get("ADM3", {})
    adm4_data = diff["levels"].get("ADM4", {})

    adm2_exclusions = {
        k: v
        for k, v in adm2_data.get("geojson_only", {}).items()
        if k in _ADM2_EXCLUSION_CODES
    }

    adm3_matches, unresolved_psgc, unresolved_geojson = _match_adm3(
        psgc_only=adm3_data.get("psgc_only", {}),
        geojson_only=adm3_data.get("geojson_only", {}),
        threshold=threshold,
        huc_mapping=huc_mapping if huc_mapping else None,
    )

    adm4_remapped, adm4_unmatched_psgc, adm4_unmatched_geojson = _match_adm4_by_parent(
        adm3_matches=adm3_matches,
        psgc_only_adm4=adm4_data.get("psgc_only", {}),
        geojson_only_adm4=adm4_data.get("geojson_only", {}),
        huc_mapping=huc_mapping if huc_mapping else None,
    )

    return ReconcileResult(
        date=date,
        matches=adm3_matches,
        unresolved_psgc=unresolved_psgc,
        unresolved_geojson=unresolved_geojson,
        adm2_exclusions=adm2_exclusions,
        adm4_remapped=adm4_remapped,
        adm4_unmatched_psgc=adm4_unmatched_psgc,
        adm4_unmatched_geojson=adm4_unmatched_geojson,
    )
