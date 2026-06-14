"""Phase 5 — Bucket classified features by ``psgc_type`` and write per-type
GeoJSON files plus a classification report."""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

OUTPUT_MAP: dict[str, str] = {
    "country": "country",
    "region": "regions",
    "province": "provinces",
    "municipality": "municipalities",
    "highly_urbanized_city": "highly_urbanized_cities",
    "independent_component_city": "independent_component_cities",
    "component_city": "component_cities",
    "submunicipality": "submunicipalities",
    "barangay": "barangays",
    "special_geographic_area": "special_geographic_areas",
}

_METHOD_KEYS = ("exact", "huc_map", "fuzzy", "non_administrative", "unresolved")

_EXPECTED_SUBMUNI_PCIDES = [
    "PH1380601",
    "PH1380602",
    "PH1380603",
    "PH1380604",
    "PH1380605",
    "PH1380606",
    "PH1380607",
    "PH1380608",
    "PH1380609",
    "PH1380610",
    "PH1380611",
    "PH1380612",
    "PH1380613",
    "PH1380614",
]


def bucket_features(
    classified: dict[int, dict],
) -> dict[str, list[dict]]:
    """Group features by ``psgc_type`` across all adm levels.

    ``classified`` maps adm_level → FeatureCollection dict. Features whose
    ``psgc_type`` has no dedicated output file (e.g. ``mm_district``,
    ``huc_isabela``, ``unresolved``) are routed to the ``unresolved`` bucket so
    that no input feature is ever dropped.
    """
    buckets: dict[str, list[dict]] = defaultdict(list)
    for adm_level, data in classified.items():
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            ptype = props.get("psgc_type", "unresolved")
            if ptype in OUTPUT_MAP:
                bucket_key = ptype
            elif ptype == "non_administrative":
                bucket_key = "non_administrative"
            else:
                bucket_key = "unresolved"
            buckets[bucket_key].append(feature)
    return buckets


def _match_summary(features: list[dict]) -> dict[str, int]:
    counter: Counter = Counter()
    for feature in features:
        method = feature.get("properties", {}).get("match_method", "unresolved")
        if method not in _METHOD_KEYS:
            method = "unresolved"
        counter[method] += 1
    return {k: counter.get(k, 0) for k in _METHOD_KEYS}


def _feature_collection(
    features: list[dict],
    psgc_type: str,
    psgc_version: str,
    namria_version: str,
) -> dict:
    return {
        "type": "FeatureCollection",
        "metadata": {
            "psgc_type": psgc_type,
            "psgc_version": psgc_version,
            "namria_version": namria_version,
            "feature_count": len(features),
            "match_summary": _match_summary(features),
        },
        "features": features,
    }


def write_hierarchical(
    buckets: dict[str, list[dict]],
    output_dir: Path,
    *,
    psgc_version: str,
    namria_version: str,
    expected_counts: dict[str, int] | None = None,
    submunicipality_note: str | None = None,
) -> dict:
    """Write per-type GeoJSON files + ``classification_report.json``.

    Returns the report dict (also written to disk).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    report: dict = {
        "psgc_version": psgc_version,
        "namria_version": namria_version,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "per_type": {},
        "expected_counts": expected_counts or {},
        "count_reconciliation": {},
        "limitations": {},
    }

    written_total = 0
    for psgc_type, filename in OUTPUT_MAP.items():
        features = buckets.get(psgc_type, [])
        out_path = output_dir / f"{filename}.geojson"
        payload = _feature_collection(features, psgc_type, psgc_version, namria_version)
        with open(out_path, "w") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        written_total += len(features)
        report["per_type"][psgc_type] = {
            "file": out_path.name,
            "feature_count": len(features),
            "match_summary": payload["metadata"]["match_summary"],
        }
        if expected_counts and psgc_type in expected_counts:
            exp = expected_counts[psgc_type]
            report["count_reconciliation"][psgc_type] = _reconcile(
                len(features), exp.get("count"), exp.get("tolerance")
            )

    unresolved_features = buckets.get("unresolved", [])
    if unresolved_features:
        out_path = output_dir / "unresolved.geojson"
        payload = _feature_collection(
            unresolved_features, "unresolved", psgc_version, namria_version
        )
        with open(out_path, "w") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        written_total += len(unresolved_features)
        report["per_type"]["unresolved"] = {
            "file": out_path.name,
            "feature_count": len(unresolved_features),
            "match_summary": payload["metadata"]["match_summary"],
            "type_breakdown": dict(
                Counter(
                    f.get("properties", {}).get("psgc_type", "unresolved")
                    for f in unresolved_features
                )
            ),
        }

    non_admin_features = buckets.get("non_administrative", [])
    if non_admin_features:
        out_path = output_dir / "non_administrative.geojson"
        payload = _feature_collection(
            non_admin_features, "non_administrative", psgc_version, namria_version
        )
        with open(out_path, "w") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        written_total += len(non_admin_features)
        report["per_type"]["non_administrative"] = {
            "file": out_path.name,
            "feature_count": len(non_admin_features),
            "match_summary": payload["metadata"]["match_summary"],
        }

    report["total_written"] = written_total

    sub_count = len(buckets.get("submunicipality", []))
    if sub_count == 0:
        report["limitations"]["submunicipalities"] = {
            "reason": (
                "NAMRIA ADM4 contains no separate polygons for the 14 Manila "
                "submunicipalities (they exist only as barangay parents)."
            ),
            "expected_pcodes": _EXPECTED_SUBMUNI_PCIDES,
            "note": submunicipality_note
            or "Aggregation from barangays is out of scope.",
        }

    report_path = output_dir / "classification_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(
        "Hierarchical output written to %s (%d features across %d files)",
        output_dir,
        written_total,
        len(report["per_type"]),
    )
    return report


def _reconcile(actual: int, expected: int | None, tolerance: int) -> dict:
    if expected is None:
        return {"actual": actual, "expected": None, "ok": True}
    diff = actual - expected
    ok = abs(diff) <= tolerance
    return {
        "actual": actual,
        "expected": expected,
        "tolerance": tolerance,
        "diff": diff,
        "ok": ok,
    }


_TYPE_DISPLAY: dict[str, str] = {
    "country": "Country (ADM0)",
    "region": "Region",
    "province": "Province",
    "municipality": "Municipality",
    "highly_urbanized_city": "Highly Urbanized City",
    "independent_component_city": "Independent Component City",
    "component_city": "Component City",
    "submunicipality": "Submunicipality",
    "special_geographic_area": "Special Geographic Area",
    "barangay": "Barangay",
    "unresolved": "Unresolved",
    "non_administrative": "Non-administrative",
}


def _type_label(ptype: str) -> str:
    return _TYPE_DISPLAY.get(ptype, ptype.replace("_", " ").title())


def write_summary_markdown(report: dict, output_dir: Path) -> Path:
    """Render ``classification_report.json`` as a human-readable ``summary.md``."""
    lines: list[str] = []
    psgc_version = report.get("psgc_version", "?")
    namria_version = report.get("namria_version", "?")
    generated = report.get("generated_at", "?")

    lines.append("# Hierarchical GeoJSON — Classification Summary\n")
    lines.append(f"- **PSGC version:** `{psgc_version}`")
    lines.append(f"- **NAMRIA version:** `{namria_version}`")
    lines.append(f"- **Generated:** {generated}")
    lines.append(f"- **Total features written:** {report.get('total_written', 0):,}")
    conservation = report.get("validation", {})
    status = "OK" if conservation.get("ok") else "FAILED"
    lines.append(f"- **Feature conservation:** {status}")
    lines.append("")

    lines.append("## Output Files\n")
    lines.append("| Type | File | Features | Exact | HUC map | Fuzzy | Unresolved |")
    lines.append("|------|------|---------:|------:|--------:|------:|-----------:|")
    for ptype, info in report.get("per_type", {}).items():
        ms = info.get("match_summary", {})
        lines.append(
            f"| {_type_label(ptype)} | `{info.get('file', '')}` | "
            f"{info.get('feature_count', 0):,} | "
            f"{ms.get('exact', 0):,} | {ms.get('huc_map', 0):,} | "
            f"{ms.get('fuzzy', 0):,} | {ms.get('unresolved', 0):,} |"
        )
    lines.append("")

    rec = report.get("count_reconciliation", {})
    if rec:
        lines.append("## Count Reconciliation (NAMRIA output vs PSGC reference)\n")
        lines.append("| Type | Actual | Expected | Diff | Tolerance | Status |")
        lines.append("|------|-------:|---------:|-----:|----------:|:------:|")
        for ptype, info in rec.items():
            actual = info.get("actual", 0)
            expected = info.get("expected")
            exp_str = f"{expected:,}" if expected is not None else "—"
            diff = info.get("diff", 0)
            tol = info.get("tolerance", 0)
            ok = "✓" if info.get("ok", True) else "✗"
            lines.append(
                f"| {_type_label(ptype)} | {actual:,} | {exp_str} | "
                f"{diff:+,} | ±{tol:,} | {ok} |"
            )
        lines.append("")

    gaps = report.get("coverage_gaps", {})
    summary = gaps.get("summary", {})
    if summary:
        lines.append("## Coverage Gaps\n")
        lines.append(
            f"- **PSGC entities without a NAMRIA polygon:** "
            f"{summary.get('psgc_entities_without_namria_polygon', 0):,}"
        )
        lines.append(
            f"- **NAMRIA features without a PSGC match:** "
            f"{summary.get('namria_features_without_psgc_match', 0):,}"
        )
        lines.append("")

    psgc_missing = gaps.get("psgc_without_namria", {})
    if psgc_missing:
        lines.append("### PSGC → NAMRIA (entities with no NAMRIA polygon)\n")
        lines.append("| Type | Expected | Matched | Missing |")
        lines.append("|------|---------:|--------:|--------:|")
        for ptype, info in sorted(psgc_missing.items()):
            if info.get("missing", 0) == 0:
                continue
            lines.append(
                f"| {_type_label(ptype)} | {info.get('expected', 0):,} | "
                f"{info.get('matched', 0):,} | {info.get('missing', 0):,} |"
            )
        lines.append("")
        for ptype, info in sorted(psgc_missing.items()):
            items = info.get("items", [])
            if not items:
                continue
            lines.append(
                f"<details><summary><b>{_type_label(ptype)}</b> — {len(items)} missing</summary>\n"
            )
            lines.append("")
            lines.append("| PSGC Code | Name |")
            lines.append("|-----------|------|")
            for it in items[:200]:
                lines.append(f"| {it['psgc_code']} | {it['name']} |")
            if len(items) > 200:
                lines.append(
                    f"| … | _{len(items) - 200} more (see classification_report.json)_ |"
                )
            lines.append("\n</details>\n")

    namria_missing = gaps.get("namria_without_psgc", {})
    if namria_missing and namria_missing.get("count", 0):
        lines.append("### NAMRIA → PSGC (features that failed classification)\n")
        lines.append("| Type | ADM Level | Name | NAMRIA PCODE | PSGC Status |")
        lines.append("|------|-----------|------|--------------|-------------|")
        for it in namria_missing.get("items", []):
            lines.append(
                f"| {_type_label(it.get('psgc_type', 'unresolved'))} | "
                f"{it.get('adm_level', '?')} | {it.get('name', '')} | "
                f"`{it.get('namria_pcode', '')}` | {it.get('psgc_status', '')} |"
            )
        lines.append("")

    limitations = report.get("limitations", {})
    if limitations:
        lines.append("## Known Limitations\n")
        for key, info in limitations.items():
            lines.append(f"- **{_type_label(key)}:** {info.get('reason', info)}")
            if info.get("note"):
                lines.append(f"  - {info['note']}")
        lines.append("")

    summary_path = output_dir / "summary.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("Markdown summary written to %s", summary_path)
    return summary_path


def validate_conservation(input_counts: dict[int, int], report: dict) -> list[str]:
    """Return a list of conservation error strings (empty if all good)."""
    errors: list[str] = []
    total_in = sum(input_counts.values())
    total_out = report.get("total_written", 0)
    if total_in != total_out:
        errors.append(
            f"Feature conservation failed: input={total_in} output={total_out}"
        )
    return errors
