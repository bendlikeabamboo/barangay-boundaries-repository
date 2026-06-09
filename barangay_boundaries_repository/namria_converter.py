from __future__ import annotations

import logging
import re
from pathlib import Path

import geopandas as gpd
import shapely

logger = logging.getLogger(__name__)

_ADM0_PATTERN = re.compile(r"phl_admbnda_adm0_singlepart_psa_namria_\d+\.shp$", re.IGNORECASE)
_ADMN_PATTERN = re.compile(r"phl_admbnda_adm([1-4])_psa_namria_\d+\.shp$", re.IGNORECASE)

_DROP_COLUMNS = {
    "Shape_Leng",
    "Shape_Area",
    "AREA_SQKM",
    "date",
    "validOn",
    "validTo",
}


def discover_shapefiles(source_dir: Path) -> list[tuple[int, Path]]:
    results: list[tuple[int, Path]] = []
    for shp in sorted(source_dir.glob("*.shp")):
        name = shp.name
        m = _ADM0_PATTERN.match(name)
        if m:
            results.append((0, shp))
            continue
        m = _ADMN_PATTERN.match(name)
        if m:
            results.append((int(m.group(1)), shp))
    return results


def convert_shapefile_to_geojson(
    shp_path: Path,
    output_path: Path,
    tolerance: float = 0.005,
    drop_columns: bool = False,
) -> dict:
    gdf = gpd.read_file(shp_path)

    logger.info(f"Read {len(gdf)} features from {shp_path.name}")

    for col in ("date", "validOn", "validTo"):
        if col in gdf.columns:
            gdf[col] = gdf[col].astype(str).replace("NaT", "")

    if tolerance > 0:
        gdf.geometry = gdf.geometry.simplify(tolerance, preserve_topology=True)

    if drop_columns:
        keep = [c for c in gdf.columns if not any(c.upper() == d.upper() for d in _DROP_COLUMNS)]
        gdf = gdf[keep]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(output_path, driver="GeoJSON")

    size_mb = output_path.stat().st_size / (1024 * 1024)
    return {
        "features": len(gdf),
        "output": str(output_path),
        "size_mb": round(size_mb, 1),
    }


def convert_all(
    source_dir: Path,
    output_dir: Path,
    tolerance: float = 0.005,
    levels: list[int] | None = None,
    drop_columns: bool = False,
) -> list[dict]:
    shapefiles = discover_shapefiles(source_dir)
    if levels is not None:
        level_set = set(levels)
        shapefiles = [(lvl, p) for lvl, p in shapefiles if lvl in level_set]

    if not shapefiles:
        raise FileNotFoundError(f"No matching shapefiles found in {source_dir}")

    results = []
    for level, shp_path in shapefiles:
        output_path = output_dir / f"adm{level}.geojson"
        info = convert_shapefile_to_geojson(
            shp_path, output_path, tolerance=tolerance, drop_columns=drop_columns
        )
        logger.info(
            f"adm{level}: {info['features']} features → {info['output']} ({info['size_mb']} MB)"
        )
        results.append(info)
    return results
