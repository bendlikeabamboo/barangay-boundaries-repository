from __future__ import annotations

import logging
import re
from collections import defaultdict

from rdflib import Graph

from barangay_boundaries_repository.ingest.xlsx_parser import (
    parse_changes,
    parse_datafile,
)
from barangay_boundaries_repository.models.schemas import ChangeEventType
from barangay_boundaries_repository.rdf.builder import (
    RdfBuilder,
    _determine_parent_code,
)

logger = logging.getLogger(__name__)

_MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}

_SECTION_DATE_RE = re.compile(
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s*(to|-|–)\s*"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+(\d{4})",
    re.IGNORECASE,
)


def _parse_section_date(section_date: str) -> str | None:
    m = _SECTION_DATE_RE.match(section_date.strip())
    if not m:
        return None
    end_month = _MONTH_MAP[m.group(3).lower()]
    year = m.group(4)
    return f"{year}-{end_month}-28"


def compute_delta(
    date_from: str,
    date_to: str,
) -> Graph:
    from barangay_boundaries_repository.ingest.scanner import find_snapshot

    snap_from = find_snapshot(date_from)
    snap_to = find_snapshot(date_to)

    if not snap_from or not snap_from.datafile:
        raise FileNotFoundError(f"No datafile for snapshot {date_from}")
    if not snap_to or not snap_to.datafile:
        raise FileNotFoundError(f"No datafile for snapshot {date_to}")

    df_from = parse_datafile(snap_from.datafile.path)
    df_to = parse_datafile(snap_to.datafile.path)

    old_by_code: dict[str, object] = {r.code: r for r in df_from.rows}
    new_by_code: dict[str, object] = {r.code: r for r in df_to.rows}

    old_by_corr: dict[str, list] = defaultdict(list)
    for r in df_from.rows:
        if r.correspondence_code:
            old_by_corr[r.correspondence_code].append(r)

    new_by_corr: dict[str, list] = defaultdict(list)
    for r in df_to.rows:
        if r.correspondence_code:
            new_by_corr[r.correspondence_code].append(r)

    builder = RdfBuilder(snapshot_date=date_to)

    created_codes = set(new_by_code) - set(old_by_code)
    deleted_codes = set(old_by_code) - set(new_by_code)

    code_changes: dict[str, tuple[str, str]] = {}
    renames: dict[str, tuple[str, str]] = {}
    for corr in set(old_by_corr) & set(new_by_corr):
        old_rows = old_by_corr[corr]
        new_rows = new_by_corr[corr]
        if len(old_rows) == 1 and len(new_rows) == 1:
            old_row = old_rows[0]
            new_row = new_rows[0]
            if old_row.code != new_row.code and old_row.name == new_row.name:
                code_changes[corr] = (old_row.code, new_row.code)
            elif old_row.code != new_row.code and old_row.name != new_row.name:
                renames[corr] = (old_row.code, new_row.code)

    mergers: dict[str, tuple[str, list[str]]] = {}
    splits: dict[str, tuple[str, list[str]]] = {}
    for corr in set(old_by_corr) & set(new_by_corr):
        if len(old_by_corr[corr]) > 1 and len(new_by_corr[corr]) == 1:
            old_codes_list = [r.code for r in old_by_corr[corr]]
            surviving = new_by_corr[corr][0].code
            absorbed = [c for c in old_codes_list if c != surviving]
            if absorbed:
                mergers[corr] = (surviving, absorbed)
                for c in old_codes_list:
                    deleted_codes.discard(c)
                created_codes.discard(surviving)
        elif len(old_by_corr[corr]) == 1 and len(new_by_corr[corr]) > 1:
            old_code = old_by_corr[corr][0].code
            new_codes_list = [r.code for r in new_by_corr[corr]]
            splits[corr] = (old_code, new_codes_list)
            deleted_codes.discard(old_code)
            for c in new_codes_list:
                created_codes.discard(c)

    for corr, (old_code, new_code) in code_changes.items():
        deleted_codes.discard(old_code)
        created_codes.discard(new_code)

    for corr, (old_code, new_code) in renames.items():
        deleted_codes.discard(old_code)
        created_codes.discard(new_code)

    name_corrections: list[tuple[str, str, str]] = []
    for code in sorted(set(old_by_code) & set(new_by_code)):
        old_row = old_by_code[code]
        new_row = new_by_code[code]
        if old_row.name != new_row.name:
            name_corrections.append((code, old_row.name, new_row.name))

    transfers: list[tuple[str, str, str, str]] = []
    name_correction_codes = {nc[0] for nc in name_corrections}
    for code in sorted(set(old_by_code) & set(new_by_code)):
        if code in name_correction_codes:
            continue
        old_row = old_by_code[code]
        new_row = new_by_code[code]
        if old_row.name == new_row.name and old_row.code == new_row.code:
            old_parent = _determine_parent_code(code, old_row.geographic_level)
            new_parent = _determine_parent_code(code, new_row.geographic_level)
            if old_parent and new_parent and old_parent != new_parent:
                transfers.append((code, old_row.name, old_parent, new_parent))

    changes_log = None
    if snap_to.changes:
        changes_log = parse_changes(snap_to.changes.path)

    def _find_change_entry(code: str) -> object | None:
        if not changes_log:
            return None
        for entry in changes_log.entries:
            if entry.new_code == code or entry.old_code == code:
                return entry
        return None

    def _enrich_from_xlsx(code: str):
        entry = _find_change_entry(code)
        if not entry:
            return None, None
        effective = None
        if entry.section_date:
            effective = _parse_section_date(entry.section_date)
        legal_basis = entry.description if entry.description else None
        return legal_basis, effective

    if changes_log:
        for entry in changes_log.entries:
            if entry.unit_type_normalized != "merger":
                continue
            surviving_code = entry.new_code
            if not surviving_code or surviving_code not in new_by_code:
                continue
            srow = new_by_code[surviving_code]
            if srow.geographic_level in ("Bgy", "SubMun"):
                mun_prefix = surviving_code[:6]
            elif srow.geographic_level in ("Mun", "City"):
                mun_prefix = surviving_code[:4]
            else:
                mun_prefix = surviving_code[:2]
            absorbed_candidates: list[str] = []
            for dc in list(deleted_codes):
                if dc not in old_by_code:
                    continue
                drow = old_by_code[dc]
                if drow.geographic_level in ("Bgy", "SubMun"):
                    if dc[:6] != mun_prefix:
                        continue
                elif drow.geographic_level in ("Mun", "City"):
                    if dc[:4] != mun_prefix:
                        continue
                else:
                    if dc[:2] != mun_prefix:
                        continue
                absorbed_candidates.append(dc)
            if absorbed_candidates and surviving_code not in [m[0] for m in mergers.values()]:
                mergers[surviving_code] = (surviving_code, absorbed_candidates)
                deleted_codes.difference_update(absorbed_candidates)
                created_codes.discard(surviving_code)

    logger.info(
        "Delta %s → %s: %d created, %d deleted, %d code changes, %d renames, "
        "%d mergers, %d splits, %d name corrections, %d transfers",
        date_from, date_to, len(created_codes), len(deleted_codes),
        len(code_changes), len(renames), len(mergers), len(splits),
        len(name_corrections), len(transfers),
    )

    seq = 0

    for code in sorted(created_codes):
        row = new_by_code[code]
        builder.add_entity(
            code=row.code, name=row.name, level=row.geographic_level,
            correspondence_code=row.correspondence_code,
            city_class=row.city_class, income_class=row.income_class,
            urban_rural=row.urban_rural, population=row.population,
            status=row.status,
        )
        legal_basis, effective_date = _enrich_from_xlsx(code)
        builder.add_change_event(
            event_id=f"{seq:04d}",
            event_type=ChangeEventType.CREATION.value,
            entity_code=code,
            legal_basis=legal_basis,
            effective_date=effective_date,
            description=f"{row.name} ({row.geographic_level}) created",
        )
        seq += 1

    for code in sorted(deleted_codes):
        row = old_by_code[code]
        legal_basis, effective_date = _enrich_from_xlsx(code)
        builder.add_change_event(
            event_id=f"{seq:04d}",
            event_type=ChangeEventType.DELETION.value,
            old_code=code,
            legal_basis=legal_basis,
            effective_date=effective_date,
            description=f"{row.name} ({row.geographic_level}) removed",
        )
        seq += 1

    for corr, (old_code, new_code) in code_changes.items():
        old_row = old_by_corr[corr][0]
        new_row = new_by_corr[corr][0]
        builder.add_entity(
            code=new_code, name=new_row.name, level=new_row.geographic_level,
            correspondence_code=new_row.correspondence_code,
            city_class=new_row.city_class, income_class=new_row.income_class,
            urban_rural=new_row.urban_rural, population=new_row.population,
            status=new_row.status,
        )
        legal_basis, effective_date = _enrich_from_xlsx(new_code)
        builder.add_change_event(
            event_id=f"{seq:04d}",
            event_type=ChangeEventType.CODE_CHANGE.value,
            entity_code=new_code,
            old_code=old_code,
            legal_basis=legal_basis,
            effective_date=effective_date,
            description=f"PSGC code changed from {old_code} to {new_code}",
        )
        seq += 1

    for corr, (old_code, new_code) in renames.items():
        old_row = old_by_corr[corr][0]
        new_row = new_by_corr[corr][0]
        builder.add_entity(
            code=new_code, name=new_row.name, level=new_row.geographic_level,
            correspondence_code=new_row.correspondence_code,
            city_class=new_row.city_class, income_class=new_row.income_class,
            urban_rural=new_row.urban_rural, population=new_row.population,
            status=new_row.status,
        )
        legal_basis, effective_date = _enrich_from_xlsx(new_code)
        builder.add_change_event(
            event_id=f"{seq:04d}",
            event_type=ChangeEventType.RENAMING.value,
            entity_code=new_code,
            old_code=old_code,
            legal_basis=legal_basis,
            effective_date=effective_date,
            description=f"Renamed from {old_row.name} to {new_row.name}",
        )
        seq += 1

    for corr, (surviving, absorbed) in mergers.items():
        new_row = new_by_code[surviving]
        builder.add_entity(
            code=surviving, name=new_row.name, level=new_row.geographic_level,
            correspondence_code=new_row.correspondence_code,
            city_class=new_row.city_class, income_class=new_row.income_class,
            urban_rural=new_row.urban_rural, population=new_row.population,
            status=new_row.status,
        )
        legal_basis, effective_date = _enrich_from_xlsx(surviving)
        absorbed_names = " and ".join(
            old_by_code[c].name for c in absorbed if c in old_by_code
        )
        builder.add_change_event(
            event_id=f"{seq:04d}",
            event_type=ChangeEventType.MERGER.value,
            entity_codes=[surviving],
            old_codes=absorbed,
            legal_basis=legal_basis,
            effective_date=effective_date,
            description=f"Merger: {absorbed_names} merged into {new_row.name}",
        )
        seq += 1

    for corr, (original, split_codes) in splits.items():
        old_row = old_by_code[original]
        for sc in split_codes:
            new_row = new_by_code[sc]
            builder.add_entity(
                code=sc, name=new_row.name, level=new_row.geographic_level,
                correspondence_code=new_row.correspondence_code,
                city_class=new_row.city_class, income_class=new_row.income_class,
                urban_rural=new_row.urban_rural, population=new_row.population,
                status=new_row.status,
            )
        legal_basis, effective_date = _enrich_from_xlsx(original)
        split_names = " and ".join(
            new_by_code[c].name for c in split_codes if c in new_by_code
        )
        builder.add_change_event(
            event_id=f"{seq:04d}",
            event_type=ChangeEventType.SPLIT.value,
            entity_codes=split_codes,
            old_codes=[original],
            legal_basis=legal_basis,
            effective_date=effective_date,
            description=f"Split: {old_row.name} split into {split_names}",
        )
        seq += 1

    for code, old_name, new_name in name_corrections:
        row = new_by_code[code]
        builder.add_entity(
            code=code, name=row.name, level=row.geographic_level,
            correspondence_code=row.correspondence_code,
            old_name=old_name,
            city_class=row.city_class, income_class=row.income_class,
            urban_rural=row.urban_rural, population=row.population,
            status=row.status,
        )
        legal_basis, effective_date = _enrich_from_xlsx(code)
        builder.add_change_event(
            event_id=f"{seq:04d}",
            event_type=ChangeEventType.RENAMING.value,
            entity_code=code,
            old_code=code,
            legal_basis=legal_basis,
            effective_date=effective_date,
            description=f"Corrected name from {old_name} to {new_name}",
        )
        seq += 1

    for code, name, old_parent, new_parent in transfers:
        legal_basis, effective_date = _enrich_from_xlsx(code)
        builder.add_change_event(
            event_id=f"{seq:04d}",
            event_type=ChangeEventType.TRANSFER.value,
            entity_code=code,
            legal_basis=legal_basis,
            effective_date=effective_date,
            description=f"Transfer: {name} transferred from {old_parent} to {new_parent}",
        )
        seq += 1

    return builder.graph
