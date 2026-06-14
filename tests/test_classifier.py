"""Unit tests for the classifier cascade (plan §9.1)."""

from __future__ import annotations

import copy

import pytest

from barangay_boundaries_repository.classifier import (
    Classifier,
    assert_typed_accessors,
    build_type_index,
)
from tests.conftest import find_feature


@pytest.fixture(scope="module")
def classifier(snapshot_date: str) -> Classifier:
    return Classifier(psgc_date=snapshot_date)


def _props(**kw) -> dict:
    base = {
        "ADM1_PCODE": "",
        "ADM2_PCODE": "",
        "ADM3_PCODE": "",
        "ADM4_PCODE": "",
        "ADM1_EN": "",
        "ADM2_EN": "",
        "ADM3_EN": "",
        "ADM4_EN": "",
    }
    base.update(kw)
    return base


def test_assert_typed_accessors_passes(snapshot_date: str) -> None:
    assert_typed_accessors(snapshot_date)


def test_type_index_contains_all_types(snapshot_date: str) -> None:
    idx = build_type_index(snapshot_date)
    types = set(idx.values())
    for expected in (
        "region",
        "province",
        "municipality",
        "highly_urbanized_city",
        "independent_component_city",
        "component_city",
        "barangay",
    ):
        assert expected in types, f"missing {expected} in TYPE_INDEX"


def test_huc_baguio_via_type_index(classifier: Classifier) -> None:
    # City of Baguio is an HUC (psgc 1430300000)
    props = _props(psgc_code="1430300000", psgc_status="matched")
    ptype, method = classifier.classify(props, adm_level=3)
    assert ptype == "highly_urbanized_city"
    assert method == "exact"


def test_icc_cotabato_via_huc_map(classifier: Classifier) -> None:
    # City of Cotabato (ICC) is mapped via namria_adm3_to_psgc; its PSGC code
    # resolves through the type index as an independent component city.
    import barangay as bg

    bg.use_version(classifier.psgc_date)
    iccs = bg.iccs.to_frame()
    cotabato = iccs[iccs["name"].str.contains("Cotabato", case=False, na=False)]
    assert len(cotabato) == 1
    code = str(cotabato.iloc[0]["psgc_id"])
    props = _props(psgc_code=code, psgc_status="matched")
    ptype, method = classifier.classify(props, adm_level=3)
    assert ptype == "independent_component_city"
    assert method == "exact"


def test_municipality_adams(classifier: Classifier) -> None:
    # Adams, Ilocos Norte (municipality)
    props = _props(psgc_code="0102801000", psgc_status="matched")
    ptype, method = classifier.classify(props, adm_level=3)
    assert ptype == "municipality"


def test_unresolved_unknown_code(classifier: Classifier) -> None:
    props = _props(psgc_code="9999999999", psgc_status="unmatched")
    ptype, method = classifier.classify(props, adm_level=3)
    assert ptype == "unresolved"
    assert method == "unresolved"


def test_non_administrative(classifier: Classifier) -> None:
    props = _props(psgc_status="non-administrative")
    ptype, method = classifier.classify(props, adm_level=4)
    assert ptype == "non_administrative"
    assert method == "non_administrative"


def test_adm2_mm_district(classifier: Classifier) -> None:
    props = _props(ADM2_PCODE="PH13039", psgc_status="non-standard")
    ptype, method = classifier.classify(props, adm_level=2)
    assert ptype == "mm_district"
    assert method == "huc_map"


def test_adm2_sga_virtual(classifier: Classifier) -> None:
    props = _props(ADM2_PCODE="PH19099", psgc_status="matched")
    ptype, method = classifier.classify(props, adm_level=2)
    assert ptype == "special_geographic_area"


def test_adm2_huc_isabela(classifier: Classifier) -> None:
    props = _props(ADM2_PCODE="PH09097", psgc_status="matched")
    ptype, method = classifier.classify(props, adm_level=2)
    assert ptype == "huc_isabela"


def test_adm3_isabela_becomes_huc(classifier: Classifier) -> None:
    # ADM3 feature under the huc_isabela virtual province resolves to HUC.
    props = _props(
        ADM2_PCODE="PH09097",
        ADM3_EN="City of Isabela",
        psgc_status="mapped-no-psgc",
        psgc_code=None,
    )
    ptype, method = classifier.classify(props, adm_level=3)
    assert ptype == "highly_urbanized_city"
    assert method == "huc_map"


def test_adm3_sga_cluster(classifier: Classifier) -> None:
    props = _props(
        ADM2_PCODE="PH19099",
        ADM3_EN="Special Geographic Area - Carmen",
        psgc_status="mapped-no-psgc",
        psgc_code=None,
    )
    ptype, method = classifier.classify(props, adm_level=3)
    assert ptype == "special_geographic_area"
    assert method == "huc_map"


def test_adm4_matched_is_barangay(classifier: Classifier) -> None:
    props = _props(psgc_code="0102801001", psgc_status="matched")
    ptype, method = classifier.classify(props, adm_level=4)
    assert ptype == "barangay"
    assert method == "exact"


def test_country(classifier: Classifier) -> None:
    props = _props(psgc_status="matched")
    ptype, method = classifier.classify(props, adm_level=0)
    assert ptype == "country"
    assert method == "exact"


def test_classify_geojson_annotates(
    classifier: Classifier, enriched_adm3: dict
) -> None:
    from barangay_boundaries_repository.classifier import classify_geojson

    data = copy.deepcopy(enriched_adm3)
    data["features"] = data["features"][:50]
    classify_geojson(data, 3, classifier)
    for feature in data["features"]:
        props = feature["properties"]
        assert "psgc_type" in props
        assert "match_method" in props


def test_huc_renest_preserves_namria_adm2(
    classifier: Classifier, enriched_adm3: dict
) -> None:
    from barangay_boundaries_repository.classifier import classify_geojson

    data = copy.deepcopy(enriched_adm3)
    classify_geojson(data, 3, classifier)
    angeles = find_feature(data, ADM3_EN="Angeles City")
    props = angeles["properties"]
    assert props["psgc_type"] == "highly_urbanized_city"
    assert props["province"] is None
    assert props["namria_adm2_pcode"] == props["ADM2_PCODE"]
