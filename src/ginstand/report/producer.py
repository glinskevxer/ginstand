"""The producer's own page: their season, and the runs behind it.

The totals live a layer down with the settlement, because closing a crop year
and answering a producer both need them. What is here is the shape they get
printed in.
"""

from __future__ import annotations

from ginstand.report.table import Align, Column, Table
from ginstand.settle.season import ProducerSeason, for_producer
from ginstand.store.book import Book


def run_table(season: ProducerSeason) -> Table:
    """The runs behind a producer's season."""
    rows = tuple(
        (
            share.run,
            str(share.modules),
            f"{share.seed_cotton_pounds:,}",
            str(share.bales),
            f"{share.lint_pounds:,}",
            str(len(share.unclassed)),
        )
        for share in season.shares
    )
    return Table(
        title=f"Runs for {season.producer}, crop year {season.crop_year}",
        columns=(
            Column("run"),
            Column("modules", Align.RIGHT),
            Column("seed cotton", Align.RIGHT),
            Column("bales", Align.RIGHT),
            Column("lint", Align.RIGHT),
            Column("unclassed", Align.RIGHT),
        ),
        rows=rows,
        footers=(
            (
                "",
                str(season.modules),
                f"{season.seed_cotton_pounds:,}",
                str(season.bales),
                f"{season.lint_pounds:,}",
                str(season.unclassed),
            ),
        ),
        empty_note="nothing ginned",
    )


def page(book: Book, producer: str, crop_year: int) -> tuple[str, ...]:
    """A producer's season with the run table under it."""
    season = for_producer(book, producer, crop_year)
    return (*season.lines, "", *run_table(season).render())
