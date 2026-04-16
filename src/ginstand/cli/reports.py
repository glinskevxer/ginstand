"""Commands for the season and quality reports."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import click

from ginstand.cli.common import DATE, context, run_command
from ginstand.report import quality, season
from ginstand.report.audit import audit_table, faults
from ginstand.report.field import yield_table
from ginstand.report.recheck import overall, rate_table, turnaround
from ginstand.store.export import verify, write_all


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


@report.command("fields")
@click.option("--crop-year", type=int, required=True, help="which crop year")
@click.pass_context
def report_fields(ctx: click.Context, crop_year: int) -> None:
    """What each field yielded, best first."""
    holder = context(ctx)
    run_command(lambda: yield_table(holder.book, crop_year).render())


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
