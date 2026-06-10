from __future__ import annotations

import json
import logging
from pathlib import Path

from barangay_boundaries_repository.coverage import (
    CoverageReport,
    compute_coverage_with_huc,
    load_geojson_pcodes,
    load_psgc_pcodes,
)
from barangay_boundaries_repository.enrich import enrich_geojson
from barangay_boundaries_repository.generate_huc_mapping import generate_huc_mapping
from barangay_boundaries_repository.namria_converter import convert_all
from barangay_boundaries_repository.reconcile import reconcile

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent
_HUC_MAPPING_PATH = (
    _REPO_ROOT / "barangay_boundaries_repository" / "namria" / "huc_adm2_mapping.json"
)


def tolerance_to_folder_suffix(tolerance: float) -> str:
    s = f"{tolerance:.10f}".rstrip("0").lstrip("0")
    return "t0p" + s.lstrip(".")


def run_geojson_pipeline(
    date: str,
    tolerance: float = 0.005,
    levels: list[int] | None = None,
    reconcile_threshold: float = 0.7,
    source_dir: Path | None = None,
    *,
    skip_raw_reconcile: bool = False,
    skip_enrich: bool = False,
) -> None:
    if levels is None:
        levels = [0, 1, 2, 3, 4]

    suffix = tolerance_to_folder_suffix(tolerance)
    raw_dir = _REPO_ROOT / date / f"raw_{suffix}"
    enriched_dir = _REPO_ROOT / date / f"enriched_{suffix}"

    src_dir = source_dir or _REPO_ROOT / "namria"

    logger.info("Pipeline: date=%s tolerance=%.6f levels=%s", date, tolerance, levels)

    _step_convert(src_dir, raw_dir, tolerance, levels)
    _step_huc_mapping(raw_dir, date)
    logger.info("Loading PSGC pcodes for %s...", date)
    psgc = load_psgc_pcodes(date)
    logger.info(
        "PSGC pcodes loaded: %s",
        {lvl: len(codes) for lvl, codes in sorted(psgc.items())},
    )

    logger.info("Loading GeoJSON pcodes from %s...", raw_dir)
    geojson_pcodes = load_geojson_pcodes(raw_dir)
    logger.info(
        "GeoJSON pcodes loaded: %s",
        {lvl: len(codes) for lvl, codes in sorted(geojson_pcodes.items())},
    )

    logger.info("Computing coverage...")
    report = compute_coverage_with_huc(psgc, geojson_pcodes)
    report.date = date
    _step_write_diff(report, raw_dir)

    if not skip_raw_reconcile:
        _step_reconcile(raw_dir, reconcile_threshold, date)
        _step_write_summary(report, raw_dir, "raw")

    if not skip_enrich:
        _step_enrich(raw_dir, enriched_dir, date, levels)
        enriched_pcodes = load_geojson_pcodes(enriched_dir)
        enriched_report = compute_coverage_with_huc(
            psgc, enriched_pcodes, enriched_geojson_dir=enriched_dir
        )
        enriched_report.date = date
        _step_write_diff(enriched_report, enriched_dir)
        _step_reconcile(enriched_dir, reconcile_threshold, date)
        _step_write_summary(enriched_report, enriched_dir, "enriched")
    else:
        logger.info("Skipping enrichment")


def _step_convert(
    source_dir: Path, output_dir: Path, tolerance: float, levels: list[int]
) -> None:
    logger.info(
        "Phase: converting shapefiles (levels=%s, tolerance=%.6f)", levels, tolerance
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    results = convert_all(
        source_dir=source_dir,
        output_dir=output_dir,
        tolerance=tolerance,
        levels=levels,
    )
    for r in results:
        logger.info(
            "  Converted: %s (%d features, %.1f MB)",
            r["output"],
            r["features"],
            r["size_mb"],
        )


def _step_huc_mapping(raw_dir: Path, date: str) -> None:
    generated = generate_huc_mapping(raw_dir, date)

    existing: dict = {}
    if _HUC_MAPPING_PATH.exists():
        with open(_HUC_MAPPING_PATH) as f:
            existing = json.load(f)

    merged = {**existing, **generated}
    for key in ("cross_parent_mapping", "submunicipality_parents"):
        if key in existing and key not in generated:
            merged[key] = existing[key]

    run_mapping_path = raw_dir / "huc_adm2_mapping.json"
    with open(run_mapping_path, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    with open(_HUC_MAPPING_PATH, "w") as f:
        json.dump(merged, f, indent=2, ensure_ascii=False)

    logger.info(
        "  HUC mapping: %d virtual provinces, %d ADM3→PSGC mappings (archived to %s)",
        len(merged.get("virtual_provinces", {})),
        len(merged.get("namria_adm3_to_psgc", {})),
        run_mapping_path,
    )


def _step_write_diff(report: CoverageReport, output_dir: Path) -> None:
    diff_path = output_dir / "diff.json"
    levels_out: dict[str, dict] = {}
    for adm_level in sorted(report.levels):
        lr = report.levels[adm_level]
        levels_out[f"ADM{adm_level}"] = {
            "psgc_count": lr.psgc_count,
            "geojson_count": lr.geojson_count,
            "matched_count": lr.matched_count,
            "coverage_pct": round(lr.coverage_pct, 2),
            "psgc_only": lr.psgc_only,
            "geojson_only": lr.geojson_only,
        }
    data = {
        "date": report.date,
        "overall_coverage": round(report.overall_coverage, 2),
        "levels": levels_out,
    }
    with open(diff_path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info(
        "  Diff written to %s (coverage: %.3f%%)", diff_path, report.overall_coverage
    )


def _step_reconcile(output_dir: Path, threshold: float, date: str) -> None:
    diff_path = output_dir / "diff.json"
    result = reconcile(diff_path, threshold=threshold, as_of=date)
    recon_path = output_dir / "recon_report.json"
    out_data = {
        "date": result.date,
        "adm3_matches": [m.model_dump() for m in result.matches],
        "unresolved_psgc": result.unresolved_psgc,
        "unresolved_geojson": result.unresolved_geojson,
        "adm2_exclusions": result.adm2_exclusions,
        "adm4_remapped": result.adm4_remapped,
        "adm4_remapped_count": len(result.adm4_remapped),
        "adm4_unmatched_psgc": result.adm4_unmatched_psgc,
        "adm4_unmatched_geojson": result.adm4_unmatched_geojson,
    }
    with open(recon_path, "w") as f:
        json.dump(out_data, f, indent=2, ensure_ascii=False)
    logger.info(
        "  Reconciliation: %d ADM3 matches, %d unresolved",
        len(result.matches),
        len(result.unresolved_psgc),
    )


def _step_write_summary(report: CoverageReport, output_dir: Path, stage: str) -> None:
    summary_path = output_dir / "summary.md"
    lines: list[str] = []
    lines.append(f"# Coverage Summary ({stage}) — {report.date}\n")
    lines.append(f"**Overall coverage: {report.overall_coverage:.3f}%**\n")
    lines.append(
        "| Level | PSGC | GeoJSON | Matched | Coverage | PSGC-only | GeoJSON-only |"
    )
    lines.append(
        "|-------|------|---------|---------|----------|-----------|--------------|"
    )
    for adm_level in sorted(report.levels):
        lr = report.levels[adm_level]
        lines.append(
            f"| ADM{adm_level} | {lr.psgc_count} | {lr.geojson_count} | "
            f"{lr.matched_count} | {lr.coverage_pct:.3f}% | "
            f"{len(lr.psgc_only)} | {len(lr.geojson_only)} |"
        )
    lines.append(
        f"| **Total** | **{report.total_psgc}** | **{report.total_geojson}** | "
        f"**{report.total_matched}** | **{report.overall_coverage:.3f}%** | "
        f"**{sum(len(lr.psgc_only) for lr in report.levels.values())}** | "
        f"**{sum(len(lr.geojson_only) for lr in report.levels.values())}** |"
    )
    summary_path.write_text("\n".join(lines) + "\n")
    logger.info("  Summary written to %s", summary_path)


def _step_enrich(
    raw_dir: Path, enriched_dir: Path, date: str, levels: list[int]
) -> None:
    enriched_dir.mkdir(parents=True, exist_ok=True)
    for level in levels:
        gj_path = raw_dir / f"adm{level}.geojson"
        out_path = enriched_dir / f"adm{level}.geojson"
        if not gj_path.exists():
            logger.warning("  Skipping ADM%d: %s not found", level, gj_path)
            continue
        result = enrich_geojson(gj_path, date, out_path)
        features = len(result.get("features", []))
        logger.info("  Enriched ADM%d: %d features → %s", level, features, out_path)
