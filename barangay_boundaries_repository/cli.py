from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

from barangay_boundaries_repository.ingest.scanner import find_snapshot, scan_snapshots
from barangay_boundaries_repository.ingest.xlsx_parser import (
    parse_datafile,
    parse_changes,
)
from barangay_boundaries_repository.rdf.builder import RdfBuilder
from barangay_boundaries_repository.rdf.delta import compute_delta

_REPO_ROOT = Path(__file__).resolve().parent.parent

_FMT_EXT = {"turtle": "ttl", "json-ld": "jsonld", "nt": "nt"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


@click.group()
def cli() -> None:
    """PSGC Document-to-RDF Agent: Convert Philippine geographic code data to RDF."""


@cli.command("list")
def list_snapshots_cmd() -> None:
    """List available PSGC snapshots."""
    snapshots = scan_snapshots()
    if not snapshots:
        click.echo("No snapshots found.")
        return
    for snap in snapshots:
        files_str = ", ".join(f.file_type for f in snap.files)
        click.echo(f"  {snap.date}: {files_str}")


@cli.command("ingest")
@click.option("--date", required=True, help="Snapshot date (YYYY-MM-DD)")
@click.option("--data-dir", default=None, help="Override PSGC data directory")
def ingest_cmd(date: str, data_dir: str | None) -> None:
    """Ingest a single snapshot and print extracted data summary."""
    from barangay_boundaries_repository.ingest.pdf_parser import extract_pdf_text_sync

    snap = find_snapshot(date, data_dir=Path(data_dir) if data_dir else None)
    if snap is None:
        click.echo(f"No snapshot found for date: {date}", err=True)
        raise SystemExit(1)

    if snap.datafile:
        datafile = parse_datafile(snap.datafile.path)
        click.echo(f"Datafile: {len(datafile.rows)} rows")
        levels: dict[str, int] = {}
        for r in datafile.rows:
            levels[r.geographic_level] = levels.get(r.geographic_level, 0) + 1
        for level, count in sorted(levels.items()):
            click.echo(f"  {level}: {count}")

    if snap.changes:
        changelog = parse_changes(snap.changes.path)
        click.echo(
            f"Changes: {len(changelog.entries)} entries (2001-present), {len(changelog.historical_entries)} (1977-2000)"
        )
        types: dict[str, int] = {}
        for e in changelog.entries:
            types[e.unit_type_normalized] = types.get(e.unit_type_normalized, 0) + 1
        for t, count in sorted(types.items()):
            click.echo(f"  {t}: {count}")

    if snap.press_release:
        text = extract_pdf_text_sync(snap.press_release.path)
        click.echo(f"Press release: {len(text)} chars extracted")


@cli.command("process")
@click.option("--date", required=True, help="Snapshot date (YYYY-MM-DD)")
@click.option(
    "--output",
    default=None,
    type=click.Path(),
    help="Output file path (default: ./{date}/delta.ttl)",
)
@click.option(
    "--format", "fmt", default="turtle", type=click.Choice(["turtle", "json-ld", "nt"])
)
@click.option(
    "--full", is_flag=True, default=False, help="Output full snapshot instead of delta"
)
@click.option("--batch-size", default=50, type=int, help="LLM batch size for datafile")
def process_cmd(
    date: str, output: str | None, fmt: str, full: bool, batch_size: int
) -> None:
    """Process a snapshot: by default outputs the delta; use --full for the complete graph."""
    if output is None:
        filename = "psgc.ttl" if full else "delta.ttl"
        output = str(_REPO_ROOT / date / filename)

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    snap = find_snapshot(date)
    if snap is None:
        click.echo(f"No snapshot found for date: {date}", err=True)
        raise SystemExit(1)

    if full:
        if snap.datafile is None:
            click.echo(f"No datafile found for snapshot {date}", err=True)
            raise SystemExit(1)

        datafile = parse_datafile(snap.datafile.path)
        builder = RdfBuilder(snapshot_date=date)

        click.echo(f"Building RDF from {len(datafile.rows)} rows...")
        for row in datafile.rows:
            builder.add_entity(
                code=row.code,
                name=row.name,
                level=row.geographic_level,
                correspondence_code=row.correspondence_code,
                old_name=row.old_name,
                city_class=row.city_class,
                income_class=row.income_class,
                urban_rural=row.urban_rural,
                population=row.population,
                status=row.status,
            )

        builder.build_hierarchy_from_entities()
        click.echo(f"Graph has {len(builder.graph)} triples")

        if snap.changes:
            changelog = parse_changes(snap.changes.path)
            for i, entry in enumerate(changelog.entries):
                builder.add_change_event(
                    event_id=f"{i:04d}",
                    event_type=entry.unit_type_normalized,
                    entity_code=entry.new_code,
                    old_code=entry.old_code,
                    legal_basis=entry.description,
                    description=entry.remarks,
                )
            click.echo(f"Added {len(changelog.entries)} change events")

        builder.serialize(output, format=fmt)
        click.echo(f"Full snapshot written to {output}")
    else:
        _compute_and_write_delta(date, output, fmt)


@cli.command("process-all")
@click.option(
    "--format", "fmt", default="turtle", type=click.Choice(["turtle", "json-ld", "nt"])
)
def process_all_cmd(fmt: str) -> None:
    """Generate delta.ttl for every snapshot with a datafile."""
    snapshots = scan_snapshots()
    dates_with_datafile = [s.date for s in snapshots if s.datafile]

    prev_date: str | None = None
    for date in dates_with_datafile:
        ext = _FMT_EXT.get(fmt, "ttl")
        out_path = _REPO_ROOT / date / f"delta.{ext}"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if prev_date is None:
            click.echo(
                f"{date}: first snapshot (no predecessor), generating baseline delta..."
            )
            _generate_baseline_delta(date, out_path, fmt)
        else:
            click.echo(f"{date}: computing delta vs {prev_date}...")
            _compute_and_write_delta(date, str(out_path), fmt)

        prev_date = date


def _generate_baseline_delta(date: str, out_path: Path, fmt: str) -> None:
    snap = find_snapshot(date)
    if not snap or not snap.datafile:
        click.echo(f"  Skipping {date}: no datafile", err=True)
        return

    datafile = parse_datafile(snap.datafile.path)
    builder = RdfBuilder(snapshot_date=date)

    for i, row in enumerate(datafile.rows):
        builder.add_entity(
            code=row.code,
            name=row.name,
            level=row.geographic_level,
            correspondence_code=row.correspondence_code,
            city_class=row.city_class,
            income_class=row.income_class,
            urban_rural=row.urban_rural,
            population=row.population,
            status=row.status,
        )
        builder.add_change_event(
            event_id=f"{i:04d}",
            event_type="creation",
            entity_code=row.code,
            description=f"{row.name} ({row.geographic_level}) baseline",
        )

    builder.serialize(str(out_path), format=fmt)
    click.echo(f"  Baseline delta ({len(builder.graph)} triples) → {out_path}")


def _compute_and_write_delta(date: str, output: str, fmt: str) -> None:
    snapshots = scan_snapshots()
    dates_with_datafile = [s.date for s in snapshots if s.datafile]
    idx = dates_with_datafile.index(date)
    if idx == 0:
        _generate_baseline_delta(date, Path(output), fmt)
        return

    prev_date = dates_with_datafile[idx - 1]
    delta_graph = compute_delta(prev_date, date)

    fmt_map = {"turtle": "turtle", "ttl": "turtle", "json-ld": "json-ld", "nt": "nt"}
    rdflib_format = fmt_map.get(fmt, fmt)
    delta_graph.serialize(destination=output, format=rdflib_format)
    click.echo(f"  Delta ({len(delta_graph)} triples) → {output}")


@cli.command("delta")
@click.option("--from", "date_from", required=True, help="From snapshot date")
@click.option("--to", "date_to", required=True, help="To snapshot date")
@click.option(
    "--output",
    default=None,
    type=click.Path(),
    help="Output file path (default: ./delta.ttl)",
)
@click.option(
    "--format", "fmt", default="turtle", type=click.Choice(["turtle", "json-ld", "nt"])
)
def delta_cmd(date_from: str, date_to: str, output: str | None, fmt: str) -> None:
    """Compute RDF delta between two specific PSGC snapshots."""
    ext = _FMT_EXT.get(fmt, "ttl")
    if output is None:
        output = str(_REPO_ROOT / f"delta.{ext}")

    out_path = Path(output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    delta_graph = compute_delta(date_from, date_to)

    fmt_map = {"turtle": "turtle", "ttl": "turtle", "json-ld": "json-ld", "nt": "nt"}
    rdflib_format = fmt_map.get(fmt, fmt)
    delta_graph.serialize(destination=output, format=rdflib_format)
    click.echo(f"Delta graph ({len(delta_graph)} triples) written to {output}")


@cli.command("convert-geo")
@click.option(
    "--source",
    default=None,
    type=click.Path(exists=True),
    help="Source directory with NAMRIA shapefiles (default: ./namria)",
)
@click.option(
    "--output-dir",
    default=None,
    type=click.Path(),
    help="Output directory for GeoJSON files (default: ./2023-10-24)",
)
@click.option(
    "--tolerance",
    default=0.005,
    type=float,
    help="Douglas-Peucker simplification tolerance in degrees (default: 0.005)",
)
@click.option(
    "--levels",
    default="0,1,2,3,4",
    help="Comma-separated admin levels to convert (default: 0,1,2,3,4)",
)
@click.option(
    "--drop-columns",
    is_flag=True,
    default=False,
    help="Drop metadata columns, keep only names and pcodes",
)
def convert_geo_cmd(
    source: str | None,
    output_dir: str | None,
    tolerance: float,
    levels: str,
    drop_columns: bool,
) -> None:
    """Convert NAMRIA shapefiles to web-optimized GeoJSON."""
    from barangay_boundaries_repository.namria_converter import convert_all

    src = Path(source) if source else _REPO_ROOT / "namria"
    out = Path(output_dir) if output_dir else _REPO_ROOT / "2023-10-24"

    level_list = [int(l.strip()) for l in levels.split(",")]

    try:
        results = convert_all(
            source_dir=src,
            output_dir=out,
            tolerance=tolerance,
            levels=level_list,
            drop_columns=drop_columns,
        )
    except FileNotFoundError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)

    for r in results:
        click.echo(f"  {r['output']}: {r['features']} features ({r['size_mb']} MB)")


@cli.command("validate")
@click.option("--input", "input_path", required=True, type=click.Path(exists=True))
def validate_cmd(input_path: str) -> None:
    """Validate an RDF file can be parsed and check basic ORG ontology conformance."""
    from rdflib import Graph, Namespace
    from rdflib.namespace import RDF

    g = Graph()
    try:
        g.parse(input_path)
        click.echo(f"Loaded {len(g)} triples from {input_path}")
    except Exception as e:
        click.echo(f"Parse error: {e}", err=True)
        raise SystemExit(1)

    ORG = Namespace("http://www.w3.org/ns/org#")
    org_entities = len(
        list(g.subjects(predicate=RDF.type, object=ORG.FormalOrganization))
    )
    org_units = len(list(g.subjects(predicate=RDF.type, object=ORG.OrganizationalUnit)))
    change_events = len(list(g.subjects(predicate=RDF.type, object=ORG.ChangeEvent)))

    click.echo(f"  FormalOrganizations: {org_entities}")
    click.echo(f"  OrganizationalUnits: {org_units}")
    click.echo(f"  ChangeEvents: {change_events}")

    if org_entities + org_units == 0 and change_events == 0:
        click.echo("WARNING: No ORG ontology entities found in graph", err=True)
