from __future__ import annotations

import json
import logging

from barangay_boundaries_repository.agent.client import LLMClient
from barangay_boundaries_repository.ingest.pdf_parser import extract_pdf_text_sync
from barangay_boundaries_repository.ingest.scanner import find_snapshot
from barangay_boundaries_repository.ingest.xlsx_parser import (
    ChangeEntry,
    PsgcRow,
    parse_changes,
    parse_datafile,
)
from barangay_boundaries_repository.models.schemas import (
    BatchExtractionResult,
    ChangeEvent,
    GeographicEntity,
    RdfTriple,
)
from barangay_boundaries_repository.prompts.base import load_prompt

logger = logging.getLogger(__name__)


def _rows_to_text(rows: list[PsgcRow], start: int = 0) -> str:
    lines: list[str] = []
    for i, r in enumerate(rows[start:], start=start):
        parts = [str(i), r.code, r.name, r.correspondence_code, r.geographic_level]
        if r.old_name:
            parts.append(r.old_name)
        if r.city_class:
            parts.append(r.city_class)
        if r.income_class:
            parts.append(r.income_class)
        if r.urban_rural:
            parts.append(r.urban_rural)
        if r.population is not None:
            parts.append(str(r.population))
        if r.status:
            parts.append(r.status)
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def _entries_to_text(entries: list[ChangeEntry], max_entries: int | None = None) -> str:
    lines: list[str] = []
    subset = entries[:max_entries] if max_entries else entries
    for e in subset:
        parts = [e.entity_name or "(continuation)"]
        if e.unit_type_raw:
            parts.append(f"[{e.unit_type_raw}]")
        if e.new_code:
            parts.append(f"new:{e.new_code}")
        if e.old_code:
            parts.append(f"old:{e.old_code}")
        if e.mother_unit:
            parts.append(f"mother:{e.mother_unit}")
        if e.description:
            parts.append(f"basis:{e.description}")
        if e.remarks:
            parts.append(f"remarks:{e.remarks}")
        if e.section_date:
            parts.append(f"period:{e.section_date}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


class Pipeline:
    def __init__(self, client: LLMClient | None = None) -> None:
        self.client = client or LLMClient()

    def process_datafile(
        self, date: str, batch_size: int = 50
    ) -> list[GeographicEntity]:
        snapshot = find_snapshot(date)
        if snapshot is None:
            raise FileNotFoundError(f"No snapshot found for date: {date}")
        if snapshot.datafile is None:
            raise FileNotFoundError(f"No datafile found for snapshot {date}")

        datafile = parse_datafile(snapshot.datafile.path)
        all_entities: list[GeographicEntity] = []

        prompt = load_prompt("extract_psgc_entities")
        total = len(datafile.rows)

        for i in range(0, total, batch_size):
            batch = datafile.rows[i : i + batch_size]
            rows_text = _rows_to_text(batch, start=i)
            user_msg = prompt.render(snapshot_date=date, rows_text=rows_text)

            logger.info(
                "Processing datafile batch %d-%d / %d",
                i,
                min(i + batch_size, total),
                total,
            )

            result = self.client.complete(
                system=prompt.system,
                user=user_msg,
                output_model=BatchExtractionResult,
            )

            if isinstance(result, BatchExtractionResult):
                all_entities.extend(result.entities)

        logger.info("Extracted %d entities from %d rows", len(all_entities), total)
        return all_entities

    def process_changes(self, date: str) -> list[ChangeEvent]:
        snapshot = find_snapshot(date)
        if snapshot is None:
            raise FileNotFoundError(f"No snapshot found for date: {date}")
        if snapshot.changes is None:
            raise FileNotFoundError(f"No changes file found for snapshot {date}")

        changelog = parse_changes(snapshot.changes.path)
        all_events: list[ChangeEvent] = []

        prompt = load_prompt("extract_change_events")

        batch_size = 100
        entries = changelog.entries
        total = len(entries)

        for i in range(0, total, batch_size):
            batch = entries[i : i + batch_size]
            text = _entries_to_text(batch)
            user_msg = prompt.render(snapshot_date=date, changes_text=text)

            logger.info(
                "Processing changes batch %d-%d / %d",
                i,
                min(i + batch_size, total),
                total,
            )

            result = self.client.complete(
                system=prompt.system,
                user=user_msg,
                output_model=BatchExtractionResult,
            )

            if isinstance(result, BatchExtractionResult):
                all_events.extend(result.change_events)

        logger.info(
            "Extracted %d change events from %d entries", len(all_events), total
        )
        return all_events

    def process_press_release(self, date: str) -> list[ChangeEvent]:
        snapshot = find_snapshot(date)
        if snapshot is None:
            raise FileNotFoundError(f"No snapshot found for date: {date}")
        if snapshot.press_release is None:
            raise FileNotFoundError(f"No press release found for snapshot {date}")

        text = extract_pdf_text_sync(snapshot.press_release.path)
        if not text.strip():
            logger.warning("Empty text extracted from press release for %s", date)
            return []

        prompt = load_prompt("extract_change_events")
        user_msg = prompt.render(snapshot_date=date, changes_text=text)

        result = self.client.complete(
            system=prompt.system,
            user=user_msg,
            output_model=BatchExtractionResult,
        )

        if isinstance(result, BatchExtractionResult):
            return result.change_events
        return []

    def generate_rdf_triples(
        self,
        entities: list[GeographicEntity],
        changes: list[ChangeEvent],
        snapshot_date: str,
    ) -> list[RdfTriple]:
        prompt = load_prompt("map_to_org_rdf")

        entities_text = _entities_to_text(entities[:200])
        changes_text = _changes_to_text(changes[:200])

        user_msg = prompt.render(
            snapshot_date=snapshot_date,
            entities_text=entities_text,
            changes_text=changes_text,
        )

        result = self.client.complete(
            system=prompt.system,
            user=user_msg,
            output_model=list[RdfTriple],
        )

        if isinstance(result, str):
            data = json.loads(result)
            return [RdfTriple(**t) for t in data]
        if isinstance(result, list):
            return result
        return []


def _entities_to_text(entities: list[GeographicEntity]) -> str:
    lines: list[str] = []
    for e in entities:
        parts = [e.code, e.name, e.geographic_level]
        if e.correspondence_code:
            parts.append(f"corr:{e.correspondence_code}")
        if e.old_name:
            parts.append(f"old:{e.old_name}")
        if e.city_class:
            parts.append(f"class:{e.city_class}")
        if e.income_class:
            parts.append(f"income:{e.income_class}")
        if e.urban_rural:
            parts.append(f"u/r:{e.urban_rural}")
        if e.population is not None:
            parts.append(f"pop:{e.population}")
        if e.status:
            parts.append(f"status:{e.status}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)


def _changes_to_text(changes: list[ChangeEvent]) -> str:
    lines: list[str] = []
    for c in changes:
        parts = [f"[{c.event_type}]", c.entity_name]
        if c.new_code:
            parts.append(f"new:{c.new_code}")
        if c.old_code:
            parts.append(f"old:{c.old_code}")
        if c.old_name:
            parts.append(f"old_name:{c.old_name}")
        if c.legal_basis:
            parts.append(f"basis:{c.legal_basis}")
        if c.effective_date:
            parts.append(f"eff:{c.effective_date}")
        if c.plebiscite_date:
            parts.append(f"pleb:{c.plebiscite_date}")
        if c.mother_unit:
            parts.append(f"mother:{c.mother_unit}")
        if c.description:
            parts.append(f"desc:{c.description}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)
