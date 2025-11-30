"""Commands for the season and quality reports."""

from __future__ import annotations

import click

from ginstand.cli.common import context, run_command
from ginstand.report import quality, season


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
