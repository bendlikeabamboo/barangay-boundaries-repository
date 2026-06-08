from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote

from barangay_boundaries_repository.config import settings

_DATAFILE_RE = re.compile(r"(?i)(Publication.?Datafile|Datafile\d).*\.xlsx")
_CHANGES_RE = re.compile(r"(?i)(Summary.*Changes|Changes.*ema).*\.xlsx")
_PRESS_RE = re.compile(r"(?i)Press.?Release.*\.pdf")
_PROV_SUM_RE = re.compile(r"(?i)(National.*and.*Provincial.*Summary|Provincial.*Summary).*\.xlsx")


@dataclass(frozen=True)
class SnapshotFile:
    path: Path
    file_type: str


@dataclass(frozen=True)
class Snapshot:
    date: str
    directory: Path
    files: list[SnapshotFile]

    @property
    def datafile(self) -> SnapshotFile | None:
        for f in self.files:
            if f.file_type == "datafile":
                return f
        return None

    @property
    def changes(self) -> SnapshotFile | None:
        for f in self.files:
            if f.file_type == "changes":
                return f
        return None

    @property
    def press_release(self) -> SnapshotFile | None:
        for f in self.files:
            if f.file_type == "press_release":
                return f
        return None

    @property
    def prov_summary(self) -> SnapshotFile | None:
        for f in self.files:
            if f.file_type == "prov_summary":
                return f
        return None


def _classify_file(filename: str) -> str | None:
    patterns = [
        ("datafile", _DATAFILE_RE),
        ("changes", _CHANGES_RE),
        ("press_release", _PRESS_RE),
        ("prov_summary", _PROV_SUM_RE),
    ]
    for ftype, pattern in patterns:
        if pattern.search(filename):
            return ftype
    return None


def scan_snapshots(data_dir: Path | None = None) -> list[Snapshot]:
    base = data_dir or settings.psgc_data_dir
    if not base.is_dir():
        raise FileNotFoundError(f"PSGC data directory not found: {base}")

    snapshots: list[Snapshot] = []
    for entry in sorted(base.iterdir()):
        if not entry.is_dir():
            continue
        date_str = entry.name
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str):
            continue

        files: list[SnapshotFile] = []
        for child in sorted(entry.iterdir()):
            if child.is_file():
                decoded_name = re.sub(r"%[0-9A-Fa-f]{2}", lambda m: unquote(m.group()), child.name)
                ftype = _classify_file(decoded_name)
                if ftype:
                    files.append(SnapshotFile(path=child, file_type=ftype))

        snapshots.append(Snapshot(date=date_str, directory=entry, files=files))

    return snapshots


def find_snapshot(date: str, data_dir: Path | None = None) -> Snapshot | None:
    for snap in scan_snapshots(data_dir):
        if snap.date == date:
            return snap
    return None
