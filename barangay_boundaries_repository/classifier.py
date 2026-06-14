"""Phase 4 — Classify enriched GeoJSON features by PSGC administrative type.

Operates on the output of :mod:`enrich` (features already carry ``psgc_id``,
``psgc_code``, ``psgc_name``, ``psgc_status``, ``match_confidence``). For each
feature this module assigns two new properties:

* ``psgc_type``      — canonical PSGC administrative level
                       (``region``/``province``/``municipality``/
                       ``highly_urbanized_city``/``independent_component_city``/
                       ``component_city``/``submunicipality``/``barangay``/
                       ``special_geographic_area``/``country``) or a virtual/
                       sentinel value (``mm_district``/``huc_isabela``/
                       ``non_administrative``/``unresolved``).
* ``match_method``   — how the type was resolved
                       (``exact``/``huc_map``/``fuzzy``/``non_administrative``/
                       ``unresolved``).

The vast majority of features resolve via an in-memory ``psgc_id → type`` index
built once from the typed ``barangay`` accessors; only genuinely unresolved ADM3
features fall through to a ``search_fuzzy`` cascade.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import barangay as bg

logger = logging.getLogger(__name__)

_MAPPING_PATH = Path(__file__).resolve().parent / "namria" / "huc_adm2_mapping.json"

_TYPED_ACCESSORS: list[tuple[str, str]] = [
    ("regions", "region"),
    ("provinces", "province"),
    ("municipalities", "municipality"),
    ("hucs", "highly_urbanized_city"),
    ("iccs", "independent_component_city"),
    ("component_cities", "component_city"),
    ("submunicipalities", "submunicipality"),
    ("special_geographic_areas", "special_geographic_area"),
    ("barangays", "barangay"),
]

_STATUS_TO_METHOD = {
    "matched": "exact",
    "fuzzy": "fuzzy",
    "mapped-no-psgc": "huc_map",
    "non-standard": "huc_map",
}

_VIRTUAL_TYPE_TO_PSGC_TYPE = {
    "sga": "special_geographic_area",
    "huc_isabela": "highly_urbanized_city",
}

_FUZZY_CASCADE = [
    ("highly_urbanized_city", ["highly_urbanized_city"], 85.0),
    ("independent_component_city", ["independent_component_city"], 85.0),
    ("component_city", ["component_city"], 85.0),
    ("municipality", ["municipality"], 80.0),
]


def assert_typed_accessors(psgc_date: str) -> None:
    """Fail loudly if typed city accessors are empty (stale-cache symptom)."""
    bg.use_version(psgc_date)
    if len(bg.hucs.to_frame()) == 0:
        raise RuntimeError(
            f"bg.hucs is empty for {psgc_date}. Run `python -m barangay cache "
            "clear` and retry. Typed city accessors are required for "
            "classification."
        )


def build_type_index(psgc_date: str) -> dict[str, str]:
    """Build ``{psgc_id(10-digit): psgc_type}`` from all typed accessors."""
    bg.use_version(psgc_date)
    index: dict[str, str] = {}
    for attr, type_name in _TYPED_ACCESSORS:
        df = getattr(bg, attr).to_frame()
        if len(df) == 0:
            continue
        for pid in df["psgc_id"]:
            index[str(pid)] = type_name
    logger.info("TYPE_INDEX built (%d entries) for %s", len(index), psgc_date)
    return index


def build_parent_name_indexes(
    psgc_date: str,
) -> tuple[dict[str, str], dict[str, str]]:
    """Return ``(region_index, province_index)`` keyed by 2/5-digit pcode → name."""
    bg.use_version(psgc_date)
    region_index: dict[str, str] = {}
    for _, row in bg.regions.to_frame().iterrows():
        region_index["PH" + str(row["psgc_id"])[:2]] = row.iloc[0]
    province_index: dict[str, str] = {}
    for _, row in bg.provinces.to_frame().iterrows():
        province_index["PH" + str(row["psgc_id"])[:5]] = row.iloc[0]
    return region_index, province_index


def load_huc_mapping() -> dict:
    if not _MAPPING_PATH.exists():
        return {}
    with open(_MAPPING_PATH) as f:
        return json.load(f)


class Classifier:
    """Stateful classifier holding all indexes needed for the cascade."""

    def __init__(
        self,
        psgc_date: str,
        type_index: dict[str, str] | None = None,
        huc_mapping: dict | None = None,
    ) -> None:
        self.psgc_date = psgc_date
        assert_typed_accessors(psgc_date)
        self.type_index = type_index or build_type_index(psgc_date)
        self.huc_mapping = (
            huc_mapping if huc_mapping is not None else load_huc_mapping()
        )
        self.virtual_provinces = self.huc_mapping.get("virtual_provinces", {})
        self.adm3_to_psgc = self.huc_mapping.get("namria_adm3_to_psgc", {})
        self._region_index, self._province_index = build_parent_name_indexes(psgc_date)

    def classify(self, props: dict, adm_level: int) -> tuple[str, str]:
        """Return ``(psgc_type, match_method)`` for a single feature's props."""
        status = props.get("psgc_status")

        if status == "non-administrative":
            return "non_administrative", "non_administrative"

        if adm_level == 0:
            return "country", "exact"

        psgc_code = props.get("psgc_code")
        if psgc_code:
            ptype = self.type_index.get(str(psgc_code))
            if ptype:
                return ptype, _STATUS_TO_METHOD.get(status, status or "exact")

        if adm_level == 2:
            resolved = self._classify_adm2_virtual(props)
            if resolved:
                return resolved

        if adm_level == 3:
            resolved = self._classify_adm3_virtual(props)
            if resolved:
                return resolved
            resolved = self._classify_adm3_fuzzy(props)
            if resolved:
                return resolved

        if adm_level == 4:
            if status in ("matched", "fuzzy") and psgc_code:
                return "barangay", _STATUS_TO_METHOD.get(status, "exact")

        return "unresolved", "unresolved"

    def _classify_adm2_virtual(self, props: dict) -> tuple[str, str] | None:
        pcode = props.get("ADM2_PCODE", "")
        vp = self.virtual_provinces.get(pcode)
        if not vp:
            return None
        vp_type = vp.get("type", "")
        if vp_type == "sga":
            return "special_geographic_area", "huc_map"
        if vp_type == "huc_isabela":
            return "huc_isabela", "huc_map"
        if vp_type == "mm_district":
            return "mm_district", "huc_map"
        return None

    def _classify_adm3_virtual(self, props: dict) -> tuple[str, str] | None:
        adm2_pcode = props.get("ADM2_PCODE", "")
        vp = self.virtual_provinces.get(adm2_pcode)
        if not vp:
            return None
        vp_type = vp.get("type", "")
        if vp_type == "sga":
            return "special_geographic_area", "huc_map"
        if vp_type == "huc_isabela":
            return "highly_urbanized_city", "huc_map"
        return None

    def _classify_adm3_fuzzy(self, props: dict) -> tuple[str, str] | None:
        """``search_fuzzy`` cascade for genuinely unresolved ADM3 features.

        Only invoked for the small residual of ADM3 features that did not
        resolve via the type index or virtual-province map. Post-filters each
        result by parent region/province consistency (edge cases #8/#15).
        """
        from barangay.models import AdminLevel
        from barangay.search import search_fuzzy

        name = props.get("ADM3_EN", "")
        if not name:
            return None

        region_pcode = props.get("ADM1_PCODE", "")
        province_name = props.get("ADM2_EN", "")

        level_map = {
            "highly_urbanized_city": AdminLevel.HIGHLY_URBANIZED_CITY,
            "independent_component_city": AdminLevel.INDEPENDENT_COMPONENT_CITY,
            "component_city": AdminLevel.COMPONENT_CITY,
            "municipality": AdminLevel.MUNICIPALITY,
        }

        for type_name, hooks, threshold in _FUZZY_CASCADE:
            try:
                results = search_fuzzy(
                    name,
                    level=level_map[type_name],
                    match_hooks=hooks,
                    threshold=threshold,
                    limit=5,
                    as_of=self.psgc_date,
                )
            except Exception as exc:
                logger.warning("search_fuzzy failed for %r: %s", name, exc)
                continue
            for r in results:
                if self._parent_consistent(r.record, region_pcode, province_name):
                    return type_name, "fuzzy"
        return None

    def _parent_consistent(self, record, region_pcode: str, province_name: str) -> bool:
        """True if a fuzzy result's PSGC parent agrees with the feature's parent."""
        parent_id = str(getattr(record, "parent_psgc_id", "") or "")
        if not parent_id:
            return True
        result_region = "PH" + parent_id[:2]
        if region_pcode and result_region != region_pcode:
            return False
        return True


def classify_geojson(
    data: dict,
    adm_level: int,
    classifier: Classifier,
) -> dict:
    """Annotate every feature in a FeatureCollection with ``psgc_type``/
    ``match_method`` (and SGA flag for ADM4). Returns the same dict."""
    features = data.get("features", [])
    sga_adm2_pcodes = {
        pcode
        for pcode, vp in classifier.virtual_provinces.items()
        if vp.get("type") == "sga"
    }

    for feature in features:
        props = feature.setdefault("properties", {})
        ptype, method = classifier.classify(props, adm_level)
        props["psgc_type"] = ptype
        props["match_method"] = method

        if adm_level == 4:
            props["sga_member"] = props.get("ADM2_PCODE", "") in sga_adm2_pcodes

        _renest_hierarchy(props, adm_level, classifier)

    return data


def _renest_hierarchy(props: dict, adm_level: int, classifier: Classifier) -> None:
    """Re-nest HUCs/ICCs (PSGC parent = region) for ADM3 features.

    Preserves the original NAMRIA province in ``namria_adm2_pcode`` and clears
    the PSGC-inconsistent province field. Geometry is untouched.
    """
    if adm_level != 3:
        return
    ptype = props.get("psgc_type")
    if ptype not in ("highly_urbanized_city", "independent_component_city"):
        return
    namria_adm2 = props.get("ADM2_PCODE")
    if namria_adm2:
        props["namria_adm2_pcode"] = namria_adm2
    adm1 = props.get("ADM1_PCODE")
    if adm1:
        props["region"] = classifier._region_index.get(adm1, props.get("ADM1_EN"))
    props["province"] = None
