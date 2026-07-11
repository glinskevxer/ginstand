"""Commands for the season and quality reports."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import click

from ginstand.cli.common import DATE, NUMBER, context, run_command
from ginstand.invariants import failures as law_failures
from ginstand.model.instrument import Instrument, InstrumentKind
from ginstand.quality.calibration import (
    due_on,
    record,
    standing_on,
    unvouched_tickets,
)
from ginstand.report import quality, season
from ginstand.report.audit import audit_table, faults
from ginstand.report.compare import compare
from ginstand.report.daily import full, sheet
from ginstand.report.doctor import diagnose
from ginstand.report.field import yield_table
from ginstand.report.moisture import for_run as moisture_for_run
from ginstand.report.moisture import moisture_table
from ginstand.report.plastic import for_run, plastic_table, suspects
from ginstand.report.recheck import overall, rate_table, turnaround
from ginstand.report.table import Align, Column, Table
from ginstand.report.variety import variety_table
from ginstand.store.export import verify, write_all
from ginstand.store.importer import read_all
from ginstand.store.maintenance import backup, check, compact, counts


@click.group()
def report() -> None:
    """The reports the office runs."""


@report.command("season")
@click.option("--crop-year", type=int, required=True, help="which crop year")
@click.option("--runs", "with_runs", is_flag=True, help="add the run by run table")
@click.option("--producers", "with_producers", is_flag=True, help="add the producer table")
@click.pass_context
def report_season(
    ctx: click.Context, crop_year: int, with_runs: bool, with_producers: bool
) -> None:
    """A crop year's totals."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        lines = list(season.summary(holder.book, crop_year))
        if with_runs:
            lines.extend(("", *season.by_run(holder.book, crop_year).render()))
        if with_producers:
            lines.extend(("", *season.by_producer(holder.book, crop_year).render()))
        return tuple(lines)

    run_command(work)


@report.command("runs")
@click.option("--crop-year", type=int, required=True, help="which crop year")
@click.pass_context
def report_runs(ctx: click.Context, crop_year: int) -> None:
    """Every run in a crop year, with what it turned out."""
    holder = context(ctx)
    run_command(lambda: season.by_run(holder.book, crop_year).render())


@report.command("producers")
@click.option("--crop-year", type=int, required=True, help="which crop year")
@click.pass_context
def report_producers(ctx: click.Context, crop_year: int) -> None:
    """Every producer in a crop year, with what they put in and took out."""
    holder = context(ctx)
    run_command(lambda: season.by_producer(holder.book, crop_year).render())


@report.command("quality")
@click.option("--crop-year", type=int, required=True, help="which crop year")
@click.option(
    "--table",
    type=click.Choice(["summary", "colour", "staple", "off-schedule", "contamination"]),
    default="summary",
    show_default=True,
    help="which part of the quality report",
)
@click.pass_context
def report_quality(ctx: click.Context, crop_year: int, table: str) -> None:
    """How a crop year classed."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        if table == "summary":
            return quality.summary(holder.book, crop_year)
        if table == "colour":
            return quality.colour_spread(holder.book, crop_year).render()
        if table == "staple":
            return quality.staple_spread(holder.book, crop_year).render()
        if table == "off-schedule":
            return quality.off_schedule(holder.book, crop_year).render()
        return quality.contamination(holder.book, crop_year).render()

    run_command(work)


@report.command("audit")
@click.option("--on", type=DATE, required=True, help="the day to audit at")
@click.option("--faults-only", is_flag=True, help="leave out the queries")
@click.pass_context
def report_audit(ctx: click.Context, on: date, faults_only: bool) -> None:
    """Read the whole book looking for things that cannot be true."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        if faults_only:
            found = faults(holder.book, on)
            if not found:
                return ("no faults",)
            return tuple(note.line for note in found)
        return audit_table(holder.book, on).render()

    run_command(work)


@report.command("compare")
@click.option("--earlier", type=int, required=True, help="the older crop year")
@click.option("--later", type=int, required=True, help="the newer crop year")
@click.pass_context
def report_compare(ctx: click.Context, earlier: int, later: int) -> None:
    """Two crop years beside each other."""
    holder = context(ctx)
    run_command(lambda: compare(holder.book, earlier, later).render())


@report.command("day")
@click.option("--on", type=DATE, required=True, help="which day")
@click.option("--lists", is_flag=True, help="add the module and bale lists")
@click.pass_context
def report_day(ctx: click.Context, on: date, lists: bool) -> None:
    """Everything that happened on one day."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        if lists:
            return full(holder.book, on)
        return sheet(holder.book, on).lines

    run_command(work)


@report.command("fields")
@click.option("--crop-year", type=int, required=True, help="which crop year")
@click.pass_context
def report_fields(ctx: click.Context, crop_year: int) -> None:
    """What each field yielded, best first."""
    holder = context(ctx)
    run_command(lambda: yield_table(holder.book, crop_year).render())


@report.command("varieties")
@click.option("--crop-year", type=int, required=True, help="which crop year")
@click.pass_context
def report_varieties(ctx: click.Context, crop_year: int) -> None:
    """How each variety did, best lint per acre first."""
    holder = context(ctx)
    run_command(lambda: variety_table(holder.book, crop_year).render())


@report.command("moisture")
@click.option("--crop-year", type=int, required=True, help="which crop year")
@click.option("--run", "run_ref", default="", help="one run, rather than the season")
@click.pass_context
def report_moisture(ctx: click.Context, crop_year: int, run_ref: str) -> None:
    """Moisture in and out, and the turnout worked out on dry weight."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        if run_ref:
            return (moisture_for_run(holder.book, run_ref).line,)
        return moisture_table(holder.book, crop_year).render()

    run_command(work)


@report.command("plastic")
@click.option("--crop-year", type=int, required=True, help="which crop year")
@click.option("--run", "run_ref", default="", help="one run, with its suspect modules")
@click.pass_context
def report_plastic(ctx: click.Context, crop_year: int, run_ref: str) -> None:
    """Where the plastic came from."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        if not run_ref:
            return plastic_table(holder.book, crop_year).render()
        item = for_run(holder.book, run_ref)
        lines = [item.line]
        lines.extend(f"  film module {tag}" for tag in item.film_modules)
        return tuple(lines)

    run_command(work)


@report.command("suspects")
@click.argument("tag")
@click.pass_context
def report_suspects(ctx: click.Context, tag: str) -> None:
    """The film wrapped modules that were in this bale's run."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        found = suspects(holder.book, tag)
        if not found:
            return ("no film wrapped module went into this bale's run",)
        return found

    run_command(work)


@report.command("rechecks")
@click.option("--on", type=DATE, required=True, help="the day to work turnaround to")
@click.pass_context
def report_rechecks(ctx: click.Context, on: date) -> None:
    """How the rechecks the gin asked for turned out."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        lines = list(rate_table(holder.book).render())
        rate = overall(holder.book)
        if rate.answered:
            lines.extend(("", f"the office took {turnaround(holder.book, on)} days on average"))
        return tuple(lines)

    run_command(work)


@report.command("export")
@click.argument("folder", type=click.Path(file_okay=False, path_type=Path))
@click.pass_context
def report_export(ctx: click.Context, folder: Path) -> None:
    """Write every register out as CSV for the accountant."""
    holder = context(ctx)

    def work() -> list[str]:
        written = write_all(holder.book, folder)
        lines = [item.line for item in written]
        problems = verify(written)
        lines.extend(problems)
        lines.append(
            f"{len(written)} tables, {sum(item.rows for item in written)} rows"
            + (f", {len(problems)} short" if problems else "")
        )
        return lines

    run_command(work)


@report.command("book")
@click.pass_context
def report_book(ctx: click.Context) -> None:
    """What the whole book holds, one line per register."""
    holder = context(ctx)

    def work() -> list[str]:
        book = holder.book
        return [
            f"producers  {book.producers.count()}",
            f"leases     {book.leases.count()}",
            f"farms      {book.farms.count()}",
            f"fields     {book.fields.count()}",
            f"modules    {book.modules.count()} ({len(book.modules.unginned())} still in the yard)",
            f"runs       {book.runs.count()} ({len(book.runs.open_runs())} open)",
            f"bales      {book.bales.count()}",
            f"cards      {book.cards.count()} ({len(book.cards.unclassed_tags())} bales waiting)",
            f"holds      {len(book.holds.all_open())} open",
            f"receipts   {len(book.receipts.outstanding())} outstanding",
        ]

    run_command(work)


@click.group()
def book() -> None:
    """Looking after the book itself."""


@book.command("laws")
@click.pass_context
def book_laws(ctx: click.Context) -> None:
    """Check the package's own arithmetic laws across a spread of inputs."""
    context(ctx)

    def work() -> tuple[str, ...]:
        broken = tuple(law_failures())
        if not broken:
            return ("every law holds",)
        return (f"{len(broken)} laws broken", *broken)

    run_command(work)


@book.command("load")
@click.argument("folder", type=click.Path(file_okay=False, exists=True, path_type=Path))
@click.pass_context
def book_load(ctx: click.Context, folder: Path) -> None:
    """Read a folder of exported CSV back into an empty book."""
    holder = context(ctx)

    def work() -> list[str]:
        with holder.book.writing() as writing:
            loaded = read_all(writing, folder)
        return [
            *(item.line for item in loaded),
            f"{len(loaded)} tables, {sum(item.rows for item in loaded)} rows",
        ]

    run_command(work)


@book.command("check")
@click.option("--on", type=DATE, required=True, help="the day to check at")
@click.pass_context
def book_check(ctx: click.Context, on: date) -> None:
    """Ask everything worth asking about the book, in one page."""
    holder = context(ctx)
    run_command(lambda: diagnose(holder.book, on).lines)


@book.command("backup")
@click.argument("path", type=click.Path(dir_okay=False, path_type=Path))
@click.pass_context
def book_backup(ctx: click.Context, path: Path) -> None:
    """Copy the book to another file through sqlite's own backup."""
    holder = context(ctx)

    def work() -> list[str]:
        written = backup(holder.book, path)
        return [f"backed {holder.path} up to {written}"]

    run_command(work)


@book.command("verify")
@click.pass_context
def book_verify(ctx: click.Context) -> None:
    """Ask sqlite whether the book is still sound."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        problems = check(holder.book)
        return problems if problems else ("the book is sound",)

    run_command(work)


@book.command("counts")
@click.pass_context
def book_counts(ctx: click.Context) -> None:
    """How many rows each table holds."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        rows = tuple((table, str(n)) for table, n in counts(holder.book).items())
        return Table(
            title="Rows in the book",
            columns=(Column("table"), Column("rows", Align.RIGHT)),
            rows=rows,
        ).render()

    run_command(work)


@book.command("compact")
@click.pass_context
def book_compact(ctx: click.Context) -> None:
    """Squeeze the file down after a season's deletions."""
    holder = context(ctx)

    def work() -> list[str]:
        before = holder.path.stat().st_size if holder.path.is_file() else 0
        compact(holder.book)
        after = holder.path.stat().st_size if holder.path.is_file() else 0
        return [f"{before:,} bytes to {after:,} bytes"]

    run_command(work)


@click.group()
def instrument() -> None:
    """The instruments the gin's numbers come off."""


@instrument.command("add")
@click.argument("ref")
@click.argument("description")
@click.option(
    "--kind",
    type=click.Choice([kind.value for kind in InstrumentKind]),
    required=True,
    help="what sort of instrument it is",
)
@click.option("--serial", default="", help="the maker's serial number")
@click.pass_context
def instrument_add(ctx: click.Context, ref: str, description: str, kind: str, serial: str) -> None:
    """Put an instrument in the book."""
    holder = context(ctx)

    def work() -> list[str]:
        record_kind = InstrumentKind(kind)
        item = Instrument(ref=ref, kind=record_kind, description=description, serial=serial)
        with holder.book.writing() as writing:
            writing.instruments.add(item)
        return [
            f"added {item.ref} {item.description} ({item.kind}), checked every {item.interval} days"
        ]

    run_command(work)


@instrument.command("check")
@click.argument("ref")
@click.option("--on", type=DATE, required=True, help="the day it was checked")
@click.option("--error", type=NUMBER, required=True, help="how far out it read")
@click.option("--by", default="", help="who checked it")
@click.option("--note", default="", help="anything worth recording")
@click.pass_context
def instrument_check(
    ctx: click.Context, ref: str, on: date, error: Decimal, by: str, note: str
) -> None:
    """Log a check against an instrument."""
    holder = context(ctx)

    def work() -> list[str]:
        with holder.book.writing() as writing:
            logged = record(writing, ref, on, error, by, note)
        item = holder.book.instruments.get(ref)
        verdict = "passed" if logged.passed else "FAILED"
        return [
            f"{logged.instrument} {verdict} at {logged.error}, tolerance {item.tolerance}",
            f"next check due {logged.due(item.interval).isoformat()}",
        ]

    run_command(work)


@instrument.command("standing")
@click.option("--on", type=DATE, required=True, help="the day to ask about")
@click.option("--ref", default="", help="one instrument, rather than the ones due")
@click.pass_context
def instrument_standing(ctx: click.Context, on: date, ref: str) -> None:
    """What the instruments' calibration was on a day."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        if ref:
            return (standing_on(holder.book, ref, on).line,)
        found = due_on(holder.book, on)
        if not found:
            return ("every instrument is covered",)
        return tuple(item.line for item in found)

    run_command(work)


@instrument.command("unvouched")
@click.argument("ref")
@click.pass_context
def instrument_unvouched(ctx: click.Context, ref: str) -> None:
    """Every module weighed in while its scale was not vouched for."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        found = unvouched_tickets(holder.book, ref)
        if not found:
            return ("every ticket was written on a vouched scale",)
        return (f"{len(found)} tickets", *found)

    run_command(work)
