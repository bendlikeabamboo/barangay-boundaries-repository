"""Phase 4+5 orchestration: build PSGC-hierarchical GeoJSON from NAMRIA.

``build_hierarchical()`` runs (or reuses) the convert → enrich phases from
:mod:`geojson_pipeline`, then classifies every enriched feature by PSGC type
(:mod:`classifier`) and splits them into per-type files (:mod:`splitter`).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from barangay_boundaries_repository.classifier import (
    Classifier,
    classify_geojson,
)
from barangay_boundaries_repository.coverage import expected_counts
from barangay_boundaries_repository.geojson_pipeline import (
    tolerance_to_folder_suffix,
)
from barangay_boundaries_repository.splitter import (
    bucket_features,
    validate_conservation,
    write_hierarchical,
)

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent


def build_hierarchical(
    date: str = "2023-10-24",
    psgc_date: str = "2023-10-24",
    tolerance: float = 0.005,
    *,
    skip_convert: bool = False,
    skip_enrich: bool = False,
    repo_root: Path | None = None,
) -> dict:
    """Run the full hierarchical pipeline. Returns the classification report."""
    root = repo_root or _REPO_ROOT
    suffix = tolerance_to_folder_suffix(tolerance)
    raw_dir = root / date / f"raw_{suffix}"
    enriched_dir = root / date / f"enriched_{suffix}"
    output_dir = root / date / f"hierarchical_{suffix}"

    namria_version = _detect_namria_version(raw_dir, enriched_dir)

    if not skip_convert or not skip_enrich:
        logger.info(
            "Running convert+enrich via run_geojson_pipeline (date=%s, psgc=%s)",
            date,
            psgc_date,
        )
        from barangay_boundaries_repository.geojson_pipeline import (
            run_geojson_pipeline,
        )

        run_geojson_pipeline(
            date=date,
            tolerance=tolerance,
            levels=[0, 1, 2, 3, 4],
            skip_enrich=False,
        )
    else:
        logger.info("Reusing existing enriched output at %s", enriched_dir)

    if not enriched_dir.exists():
        raise FileNotFoundError(
            f"Enriched GeoJSON not found at {enriched_dir}. "
            "Run without --skip-enrich first."
        )

    classifier = Classifier(psgc_date=psgc_date)

    classified: dict[int, dict] = {}
    input_counts: dict[int, int] = {}
    for level in range(5):
        path = enriched_dir / f"adm{level}.geojson"
        if not path.exists():
            logger.warning("Missing enriched ADM%d: %s", level, path)
            continue
        with open(path) as f:
            data = json.load(f)
        input_counts[level] = len(data.get("features", []))
        classify_geojson(data, level, classifier)
        classified[level] = data
        logger.info("Classified ADM%d: %d features", level, input_counts[level])

    buckets = bucket_features(classified)

    exp = expected_counts(psgc_date)

    report = write_hierarchical(
        buckets,
        output_dir,
        psgc_version=psgc_date,
        namria_version=namria_version,
        expected_counts=exp,
    )

    errors = validate_conservation(input_counts, report)
    report["validation"] = {
        "conservation_errors": errors,
        "ok": not errors,
    }

    report["coverage_gaps"] = _coverage_gaps(buckets, psgc_date)

    with open(output_dir / "classification_report.json", "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    from barangay_boundaries_repository.splitter import write_summary_markdown

    write_summary_markdown(report, output_dir)

    _log_report(report, errors)
    return report


def _coverage_gaps(buckets: dict[str, list[dict]], psgc_date: str) -> dict:
    """Compute both directions of PSGC↔NAMRIA matching gaps.

    * ``psgc_without_namria`` — PSGC entities that have no corresponding
      NAMRIA polygon (per type: count + named items).
    * ``namria_without_psgc`` — NAMRIA features that failed PSGC
      classification (the unresolved bucket, broken down by psgc_type).
    """
    reference = _psgc_reference_by_type(psgc_date)
    matched = _matched_codes_per_type(buckets)

    psgc_missing: dict[str, dict] = {}
    for ptype, ref_codes in reference.items():
        if ptype == "country":
            continue
        matched_set = matched.get(ptype, set())
        missing_items = [
            {"psgc_code": code, "name": name}
            for code, name in sorted(ref_codes.items())
            if code not in matched_set
        ]
        psgc_missing[ptype] = {
            "expected": len(ref_codes),
            "matched": len(ref_codes) - len(missing_items),
            "missing": len(missing_items),
            "items": missing_items,
        }

    unresolved = buckets.get("unresolved", [])
    from collections import Counter

    namria_missing = {
        "count": len(unresolved),
        "by_type": dict(
            Counter(
                f.get("properties", {}).get("psgc_type", "unresolved")
                for f in unresolved
            )
        ),
        "items": [
            {
                "psgc_type": f.get("properties", {}).get("psgc_type"),
                "adm_level": _adm_level_of(f),
                "name": (
                    f.get("properties", {}).get("ADM4_EN")
                    or f.get("properties", {}).get("ADM3_EN")
                    or f.get("properties", {}).get("ADM2_EN")
                    or f.get("properties", {}).get("ADM1_EN")
                ),
                "namria_pcode": (
                    f.get("properties", {}).get("ADM4_PCODE")
                    or f.get("properties", {}).get("ADM3_PCODE")
                    or f.get("properties", {}).get("ADM2_PCODE")
                ),
                "psgc_status": f.get("properties", {}).get("psgc_status"),
            }
            for f in unresolved
        ],
    }

    total_psgc_missing = sum(v["missing"] for v in psgc_missing.values())
    return {
        "summary": {
            "psgc_entities_without_namria_polygon": total_psgc_missing,
            "namria_features_without_psgc_match": len(unresolved),
        },
        "psgc_without_namria": psgc_missing,
        "namria_without_psgc": namria_missing,
    }


def _psgc_reference_by_type(psgc_date: str) -> dict[str, dict[str, str]]:
    """Return ``{psgc_type: {psgc_code(10-digit): name}}`` for all PSGC entities."""
    import barangay as bg

    from barangay_boundaries_repository.classifier import _TYPED_ACCESSORS

    bg.use_version(psgc_date)
    reference: dict[str, dict[str, str]] = {}
    for attr, type_name in _TYPED_ACCESSORS:
        df = getattr(bg, attr).to_frame()
        if len(df) == 0:
            reference[type_name] = {}
            continue
        code_col = "psgc_id" if "psgc_id" in df.columns else df.columns[1]
        name_col = df.columns[0]
        reference[type_name] = {
            str(row[code_col]): str(row[name_col]) for _, row in df.iterrows()
        }
    return reference


def _matched_codes_per_type(
    buckets: dict[str, list[dict]],
) -> dict[str, set[str]]:
    """Collect resolved ``psgc_code`` sets per output bucket type."""
    matched: dict[str, set[str]] = {}
    for ptype, features in buckets.items():
        codes: set[str] = set()
        for ft in features:
            code = ft.get("properties", {}).get("psgc_code")
            if code:
                codes.add(str(code))
        matched[ptype] = codes
    return matched


def _adm_level_of(feature: dict) -> int | None:
    props = feature.get("properties", {})
    for level in (4, 3, 2, 1, 0):
        if props.get(f"ADM{level}_PCODE"):
            return level
    return None


def _detect_namria_version(raw_dir: Path, enriched_dir: Path) -> str:
    for d in (enriched_dir, raw_dir):
        adm0 = d / "adm0.geojson"
        if adm0.exists():
            try:
                with open(adm0) as f:
                    data = json.load(f)
                feats = data.get("features", [])
                if feats:
                    return (
                        feats[0].get("properties", {}).get("validOn")
                        or feats[0].get("properties", {}).get("date")
                        or "unknown"
                    )
            except Exception:
                pass
    return "unknown"


def _log_report(report: dict, errors: list[str]) -> None:
    logger.info("=== Hierarchical classification summary ===")
    for ptype, info in sorted(report.get("per_type", {}).items()):
        logger.info(
            "  %-28s %5d  %s",
            ptype,
            info.get("feature_count", 0),
            info.get("file", ""),
        )
    rec = report.get("count_reconciliation", {})
    fails = [k for k, v in rec.items() if not v.get("ok", True)]
    if fails:
        logger.warning("Count reconciliation mismatches: %s", fails)
    if errors:
        logger.error("Conservation errors: %s", errors)
    else:
        logger.info(
            "Conservation OK: %d features in → %d out",
            sum(
                report.get("per_type", {}).get(t, {}).get("feature_count", 0)
                for t in report.get("per_type", {})
            ),
            report.get("total_written", 0),
        )

    gaps = report.get("coverage_gaps", {}).get("summary", {})
    if gaps:
        logger.info(
            "Coverage gaps: %d PSGC entities without NAMRIA polygon, "
            "%d NAMRIA features without PSGC match",
            gaps.get("psgc_entities_without_namria_polygon", 0),
            gaps.get("namria_features_without_psgc_match", 0),
        )
        for ptype, info in sorted(
            report.get("coverage_gaps", {}).get("psgc_without_namria", {}).items()
        ):
            if info.get("missing", 0):
                logger.info(
                    "  PSGC-only %-24s %3d / %d",
                    ptype,
                    info["missing"],
                    info["expected"],
                )
