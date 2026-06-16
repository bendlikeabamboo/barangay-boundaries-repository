#!/usr/bin/env bash
# Build downloadable release artifacts for a processed PSGC snapshot.
#
# For the given snapshot (default: the inaugural 2023-10-24), this script stages the
# curated hierarchical per-class GeoJSON collection and:
#   1. Copies the per-class GeoJSON files (plus classification_report.json and summary.md)
#      into a staging directory.
#   2. Zips the collection into a single downloadable bundle.
#   3. Emits a machine-readable manifest.json with md5, sha256, byte size, and
#      feature count for every GeoJSON file.
#
# The enriched (adm0–adm4) and raw NAMRIA-converted GeoJSON are intermediate pipeline
# stages kept in-repo for traceability; they are not release artifacts.
#
# Usage:
#   scripts/build_release_artifacts.sh [SNAPSHOT_DATE]
#
# Output: build/<SNAPSHOT_DATE>/{barangay-boundaries-<SNAPSHOT_DATE>-hierarchical.zip,
#                              manifest.json,
#                              barangays.geojson, regions.geojson, ...,
#                              classification_report.json, summary.md}
set -euo pipefail

SNAPSHOT="${1:-2023-10-24}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${REPO_ROOT}/${SNAPSHOT}"

if [[ ! -d "${SRC_DIR}" ]]; then
  echo "error: snapshot directory not found: ${SRC_DIR}" >&2
  exit 1
fi

HIER_DIR="$(find "${SRC_DIR}" -maxdepth 1 -type d -name 'hierarchical_t*' | head -n1 || true)"

if [[ -z "${HIER_DIR}" ]]; then
  echo "error: hierarchical_t* directory missing under ${SRC_DIR}" >&2
  exit 1
fi

TOL_SUFFIX="$(basename "${HIER_DIR}" | sed 's/^hierarchical_//')"
NAMRIA_VERSION="2023-11-06"

STAGE="${REPO_ROOT}/build/${SNAPSHOT}"
rm -rf "${STAGE}"
mkdir -p "${STAGE}"

echo "==> Staging hierarchical GeoJSON from $(basename "${HIER_DIR}")"
cp "${HIER_DIR}"/*.geojson "${STAGE}"/
# Carry the classification report and human-readable summary alongside the per-class files.
# Copied unconditionally: the release workflow attaches both, so a missing artifact must
# fail here with a clear message rather than later as a confusing release-upload error.
cp "${HIER_DIR}/classification_report.json" "${HIER_DIR}/summary.md" "${STAGE}"/

echo "==> Creating hierarchical zip bundle"
python3 - "${STAGE}" "${SNAPSHOT}" <<'PYEOF'
import sys, zipfile
from pathlib import Path

stage, snapshot = Path(sys.argv[1]), sys.argv[2]

with zipfile.ZipFile(stage / f"barangay-boundaries-{snapshot}-hierarchical.zip", "w", zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(stage.glob("*.geojson")):
        zf.write(path, path.name)
PYEOF

echo "==> Generating manifest.json"
python3 - "${STAGE}" "${SNAPSHOT}" "${TOL_SUFFIX}" "${NAMRIA_VERSION}" <<'PYEOF'
import hashlib, json, sys
from pathlib import Path

stage, snapshot, tol, namria = sys.argv[1:5]
files = sorted(Path(stage).glob("*.geojson"))

def feature_count(path: Path) -> int:
    try:
        with path.open("rb") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and isinstance(data.get("features"), list):
            return len(data["features"])
    except Exception:
        return -1

entries = []
for path in files:
    raw = path.read_bytes()
    rel = path.relative_to(stage).as_posix()
    entries.append({
        "path": rel,
        "snapshot": snapshot,
        "namria_version": namria,
        "tolerance_degrees": tol,
        "format": "GeoJSON",
        "bytes": len(raw),
        "md5": hashlib.md5(raw).hexdigest(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "features": feature_count(path),
    })

manifest = {
    "dataset": "barangay-boundaries-repository",
    "snapshot": snapshot,
    "namria_version": namria,
    "tolerance_degrees": tol,
    "tier": "hierarchical (curated)",
    "attribution": {
        "psgc": "Philippine Statistics Authority (PSA)",
        "boundaries": "NAMRIA",
    },
    "files": entries,
}
(Path(stage) / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"   wrote manifest with {len(entries)} files")
PYEOF

echo "==> Done. Artifacts in ${STAGE}:"
ls -lh "${STAGE}"
