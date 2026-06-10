"""Generate HUC ADM2 mapping from NAMRIA GeoJSON and PSGC data."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import barangay as bg


def generate_huc_mapping(
    geojson_dir: Path,
    date: str,
) -> dict:
    bg.use_version(date)

    adm3_path = geojson_dir / "adm3.geojson"
    if not adm3_path.exists():
        raise FileNotFoundError(f"ADM3 GeoJSON not found: {adm3_path}")

    with open(adm3_path) as f:
        data = json.load(f)

    cities_df = bg.cities.to_frame()
    huc_cities = cities_df[cities_df["parent_psgc_id"].str.endswith("0000000", na=False)]

    huc_by_region: dict[str, list[dict]] = defaultdict(list)
    for _, row in huc_cities.iterrows():
        parent_region = str(row["parent_psgc_id"])[:2]
        huc_by_region[parent_region].append(
            {
                "psgc_id": str(row["psgc_id"]),
                "psgc_pcode": "PH" + str(row["psgc_id"])[:7],
                "name": row.iloc[0],
            }
        )

    munis_df = bg.municipalities.to_frame()
    ncr_munis = munis_df[munis_df["parent_psgc_id"] == "1300000000"]
    for _, row in ncr_munis.iterrows():
        huc_by_region["13"].append(
            {
                "psgc_id": str(row["psgc_id"]),
                "psgc_pcode": "PH" + str(row["psgc_id"])[:7],
                "name": row.iloc[0],
            }
        )

    sga_df = bg.special_geographic_areas.to_frame()

    namria_by_adm2: dict[str, list[dict]] = defaultdict(list)
    for feature in data["features"]:
        props = feature.get("properties", {})
        adm2_code = props.get("ADM2_PCODE", "")
        adm2_name = props.get("ADM2_EN", "")
        adm3_code = props.get("ADM3_PCODE", "")
        adm3_name = props.get("ADM3_EN", "")
        adm1_code = props.get("ADM1_PCODE", "")

        if adm2_code:
            namria_by_adm2[adm2_code].append(
                {
                    "adm2_code": adm2_code,
                    "adm2_name": adm2_name,
                    "adm3_code": adm3_code,
                    "adm3_name": adm3_name,
                    "adm1_code": adm1_code,
                }
            )

    provinces_df = bg.provinces.to_frame()
    province_pcodes = set("PH" + str(pid)[:5] for pid in provinces_df["psgc_id"])

    virtual_provinces: dict[str, dict] = {}
    metro_manila_districts: dict[str, list[str]] = {}
    huc_cities_under_province: dict[str, list[dict]] = {}
    namria_adm3_to_psgc: dict[str, str] = {}

    non_standard_adm2 = {
        code for code in namria_by_adm2 if code not in province_pcodes
    }

    ncr_region_code = "PH13"

    for adm2_code in sorted(namria_by_adm2):
        if adm2_code in province_pcodes:
            features = namria_by_adm2[adm2_code]
            region_code = features[0]["adm1_code"]
            region_num = region_code.replace("PH", "")
            hucs_in_region = huc_by_region.get(region_num, [])

            if not hucs_in_region:
                continue

            adm2_features = namria_by_adm2[adm2_code]
            province_hucs: list[dict] = []

            for namria_feat in adm2_features:
                namria_name = namria_feat["adm3_name"].lower()
                namria_name_clean = _sanitize(namria_name)

                best_match = None
                best_score = 0

                for huc in hucs_in_region:
                    huc_name_clean = _sanitize(huc["name"])
                    score = _name_similarity(namria_name_clean, huc_name_clean)
                    if score > best_score:
                        best_score = score
                        best_match = huc

                if best_match and best_score >= 70:
                    mapping = {
                        "namria_adm3_pcode": namria_feat["adm3_code"],
                        "psgc_code": best_match["psgc_id"],
                        "psgc_pcode": best_match["psgc_pcode"],
                        "name": namria_feat["adm3_name"],
                    }
                    province_hucs.append(mapping)
                    namria_adm3_to_psgc[namria_feat["adm3_code"]] = best_match["psgc_pcode"]

            if province_hucs:
                huc_cities_under_province[adm2_code] = province_hucs

        elif adm2_code in non_standard_adm2:
            adm2_name = namria_by_adm2[adm2_code][0]["adm2_name"]

            if "Isabela" in adm2_name and adm2_code == "PH09097":
                virtual_provinces[adm2_code] = {
                    "psgc_code": "0990100000",
                    "psgc_pcode": "PH09901",
                    "name": adm2_name,
                    "type": "huc_isabela",
                }
                for feat in namria_by_adm2[adm2_code]:
                    namria_adm3_to_psgc[feat["adm3_code"]] = "PH09901"

            elif adm2_code.startswith("PH13") and adm2_code != ncr_region_code:
                district_cities_pcodes: list[str] = []
                for feat in namria_by_adm2[adm2_code]:
                    region_num = "13"
                    best_match = _find_ncr_match(
                        feat["adm3_name"], huc_by_region.get(region_num, [])
                    )
                    if best_match:
                        namria_adm3_to_psgc[feat["adm3_code"]] = best_match["psgc_pcode"]
                        district_cities_pcodes.append(best_match["psgc_pcode"])

                virtual_provinces[adm2_code] = {
                    "psgc_code": None,
                    "psgc_pcode": None,
                    "name": adm2_name,
                    "type": "mm_district",
                }
                metro_manila_districts[adm2_code] = district_cities_pcodes

            elif "Special Geographic Area" in adm2_name:
                sga_entries = sga_df[sga_df["parent_psgc_id"] == "1900000000"]
                if len(sga_entries) > 0:
                    top_sga = sga_entries.iloc[0]
                    sga_psgc_id = str(top_sga["psgc_id"])
                    virtual_provinces[adm2_code] = {
                        "psgc_code": sga_psgc_id,
                        "psgc_pcode": "PH" + sga_psgc_id[:5],
                        "name": adm2_name,
                        "type": "sga",
                    }
                    for feat in namria_by_adm2[adm2_code]:
                        namria_adm3_to_psgc[feat["adm3_code"]] = "PH" + sga_psgc_id[:5]

    return {
        "virtual_provinces": virtual_provinces,
        "metro_manila_districts": metro_manila_districts,
        "huc_cities_under_province": huc_cities_under_province,
        "namria_adm3_to_psgc": namria_adm3_to_psgc,
    }


def _sanitize(name: str) -> str:
    n = name.lower().strip()
    for token in [
        "(capital)",
        "(pob.)",
        "(pob)",
        "pob.",
        "(not a province)",
        "city of ",
        "city",
    ]:
        n = n.replace(token, "")
    n = n.replace("(", "").replace(")", "").strip()
    return " ".join(n.split())


def _name_similarity(a: str, b: str) -> float:
    if a == b:
        return 100
    set_a = set(a.split())
    set_b = set(b.split())
    if not set_a or not set_b:
        return 0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) * 100


def _find_ncr_match(namria_name: str, ncr_entities: list[dict]) -> dict | None:
    namria_clean = _sanitize(namria_name)
    best_match = None
    best_score = 0

    for entity in ncr_entities:
        entity_clean = _sanitize(entity["name"])
        score = _name_similarity(namria_clean, entity_clean)
        if score > best_score:
            best_score = score
            best_match = entity

    if best_match and best_score >= 50:
        return best_match
    return None


if __name__ == "__main__":
    import sys

    geojson_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("2023-10-24")
    date = sys.argv[2] if len(sys.argv) > 2 else "2023-10-24"
    output_path = Path(
        sys.argv[3]
    ) if len(sys.argv) > 3 else Path(
        "barangay_boundaries_repository/namria/huc_adm2_mapping.json"
    )

    mapping = generate_huc_mapping(geojson_dir, date)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
    print(f"Mapping written to {output_path}")
    print(f"  Virtual provinces: {len(mapping['virtual_provinces'])}")
    print(f"  MM districts: {len(mapping['metro_manila_districts'])}")
    print(f"  HUC cities under province: {len(mapping['huc_cities_under_province'])}")
    print(f"  NAMRIA ADM3→PSGC: {len(mapping['namria_adm3_to_psgc'])}")
