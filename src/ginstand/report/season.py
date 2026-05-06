"""The season summary: a crop year on one page.

Everything here is a total of something already reported elsewhere, which is the
point: the figures in this report have to agree with the run sheets or one of
them is wrong. So it works off the same functions the run sheet does rather than
its own queries, and the totals themselves live a layer down in
:mod:`ginstand.ginning.season`, where the settlement can reach them too.
"""

from __future__ import annotations

from ginstand.ginning.season import totals
from ginstand.report.table import Align, Column, Table
from ginstand.store.book import Book
from ginstand.units.apportion import proportion
from ginstand.units.weight import format_pounds


def summary(book: Book, crop_year: int) -> tuple[str, ...]:
    """The season's totals as the lines that head a season report."""
    season = totals(book, crop_year)
    lines = [
        f"Crop year {crop_year}",
        f"  {season.runs} runs ({season.open_runs} open), {season.modules} modules, "
        f"{format_pounds(season.seed_cotton_pounds)} seed cotton",
        f"  {season.bales} bales, {format_pounds(season.lint_pounds)} lint",
    ]
    if season.seed_cotton_pounds:
        lines.append(f"  lint turnout {season.lint_turnout}, seed turnout {season.seed_turnout}")
    if season.bales:
        lines.append(f"  {season.lint_per_bale} lb a bale")
    return tuple(lines)


def by_run(book: Book, crop_year: int) -> Table:
    """Every run in a crop year, with what it turned out."""
    rows = []
    for run in book.runs.for_crop_year(crop_year):
        seed_cotton = book.runs.seed_cotton_in(run.ref)
        lint = book.bales.lint_pounds_for_run(run.ref)
        rows.append(
            (
                run.ref,
                run.opened.isoformat(),
                run.closed.isoformat() if run.closed else "open",
                str(len(book.runs.modules_in(run.ref))),
                f"{seed_cotton:,}",
                str(book.bales.count_for_run(run.ref)),
                f"{lint:,}",
                str(proportion(lint, seed_cotton)) if seed_cotton else "",
            )
        )
    footers: tuple[tuple[str, ...], ...] = ()
    if rows:
        season = totals(book, crop_year)
        footers = (
            (
                "",
                "",
                "",
                str(season.modules),
                f"{season.seed_cotton_pounds:,}",
                str(season.bales),
                f"{season.lint_pounds:,}",
                str(season.lint_turnout) if season.seed_cotton_pounds else "",
            ),
        )
    return Table(
        title=f"Runs in crop year {crop_year}",
        columns=(
            Column("run"),
            Column("opened"),
            Column("closed"),
            Column("modules", Align.RIGHT),
            Column("seed cotton", Align.RIGHT),
            Column("bales", Align.RIGHT),
            Column("lint", Align.RIGHT),
            Column("turnout", Align.RIGHT),
        ),
        rows=tuple(rows),
        footers=footers,
        empty_note="no runs in this crop year",
    )


def by_producer(book: Book, crop_year: int) -> Table:
    """Every producer in a crop year, with what they put in and took out."""
    seed_cotton: dict[str, int] = {}
    modules: dict[str, int] = {}
    bales: dict[str, int] = {}
    lint: dict[str, int] = {}
    from ginstand.yard.receiving import producer_of

    for run in book.runs.for_crop_year(crop_year):
        for tag in book.runs.modules_in(run.ref):
            owner = producer_of(book, tag)
            modules[owner] = modules.get(owner, 0) + 1
            seed_cotton[owner] = seed_cotton.get(owner, 0) + book.modules.get(tag).net_pounds
        for tag, owner in book.allocations.bales_for_run(run.ref).items():
            bales[owner] = bales.get(owner, 0) + 1
            lint[owner] = lint.get(owner, 0) + book.bales.get(tag).net_pounds

    rows = [
        (
            producer,
            str(modules.get(producer, 0)),
            f"{seed_cotton.get(producer, 0):,}",
            str(bales.get(producer, 0)),
            f"{lint.get(producer, 0):,}",
        )
        for producer in sorted(set(seed_cotton) | set(bales))
    ]
    return Table(
        title=f"Producers in crop year {crop_year}",
        columns=(
            Column("producer"),
            Column("modules", Align.RIGHT),
            Column("seed cotton", Align.RIGHT),
            Column("bales", Align.RIGHT),
            Column("lint", Align.RIGHT),
        ),
        rows=tuple(rows),
        empty_note="nobody ginned in this crop year",
    )
