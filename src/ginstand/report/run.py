"""The run sheet: what went into a gin run and what came out of it.

Three tables rather than one. The feed order matters to the gin manager, the
bale list matters to whoever is shipping, and the allocation matters to the
office, and none of them wants to read the other two to find their part.

The turnout line sits under the feed table because that is where the argument
about it starts: a low turnout is nearly always a question about a weight on the
feed side rather than about the bales.
"""

from __future__ import annotations

from ginstand.errors import StateError
from ginstand.ginning.allocate import plan
from ginstand.ginning.seed import seed_pounds, seed_turnout
from ginstand.ginning.turnout import turnout_for, turnout_so_far
from ginstand.report.table import Align, Column, Table
from ginstand.store.book import Book
from ginstand.units.weight import format_pounds


def feed_sheet(book: Book, run_ref: str) -> Table:
    """The modules fed into a run, in the order they went in."""
    run = book.runs.get(run_ref)
    rows = []
    for position, tag in enumerate(book.runs.modules_in(run.ref), start=1):
        module = book.modules.get(tag)
        rows.append(
            (
                str(position),
                module.tag,
                module.field,
                format_pounds(module.net_pounds),
                f"{module.moisture_pct}%",
            )
        )
    total = book.runs.seed_cotton_in(run.ref)
    state = "open" if run.is_open else f"closed {run.closed}"
    return Table(
        title=f"Gin run {run.ref} feed sheet ({state})",
        columns=(
            Column("no", Align.RIGHT),
            Column("module"),
            Column("field"),
            Column("seed cotton", Align.RIGHT),
            Column("moisture", Align.RIGHT),
        ),
        rows=tuple(rows),
        footers=(("", "", "", format_pounds(total), ""),) if rows else (),
        empty_note="nothing has been fed into this run",
    )


def bale_sheet(book: Book, run_ref: str) -> Table:
    """The bales pressed off a run, in tag order."""
    run = book.runs.get(run_ref)
    rows = []
    for bale in book.bales.for_run(run.ref):
        owner = book.allocations.owner_of(bale.tag)
        card = book.cards.find(bale.tag)
        rows.append(
            (
                bale.tag,
                bale.pressed.isoformat(),
                format_pounds(bale.net_pounds),
                f"{bale.moisture_pct}%",
                owner or "",
                card.summary if card is not None else "not classed",
            )
        )
    total = book.bales.lint_pounds_for_run(run.ref)
    return Table(
        title=f"Gin run {run.ref} bales",
        columns=(
            Column("tag"),
            Column("pressed"),
            Column("net", Align.RIGHT),
            Column("moisture", Align.RIGHT),
            Column("owner"),
            Column("classing"),
        ),
        rows=tuple(rows),
        footers=(("", "", format_pounds(total), "", "", ""),) if rows else (),
        empty_note="no bales have come off this run",
    )


def allocation_sheet(book: Book, run_ref: str) -> Table:
    """How the run's bales were divided, with the carry each side is left with."""
    run = book.runs.get(run_ref)
    split = plan(book, run.ref)
    rows = [
        (
            share.producer,
            format_pounds(share.seed_cotton_pounds),
            str(share.entitlement),
            str(share.carried_in),
            str(share.bales),
            str(share.carried_out),
        )
        for share in split.shares
    ]
    return Table(
        title=f"Gin run {run.ref} allocation",
        columns=(
            Column("producer"),
            Column("seed cotton", Align.RIGHT),
            Column("entitlement", Align.RIGHT),
            Column("carried in", Align.RIGHT),
            Column("bales", Align.RIGHT),
            Column("carried out", Align.RIGHT),
        ),
        rows=tuple(rows),
        footers=(("", format_pounds(split.seed_cotton_pounds), "", "", str(split.bales), ""),),
    )


def turnout_lines(book: Book, run_ref: str) -> tuple[str, ...]:
    """The turnout figures for a run, final if it is closed."""
    run = book.runs.get(run_ref)
    figure = turnout_so_far(book, run.ref) if run.is_open else turnout_for(book, run.ref)
    lines = [figure.line]
    seed = seed_pounds(book, run.ref)
    if seed:
        lines.append(f"seed {format_pounds(seed)}  {seed_turnout(book, run.ref)} turnout")
    return tuple(lines)


def run_sheet(book: Book, run_ref: str) -> tuple[str, ...]:
    """The whole run sheet, in the order the office reads it."""
    run = book.runs.get(run_ref)
    lines = list(feed_sheet(book, run.ref).render())
    try:
        lines.extend(("", *turnout_lines(book, run.ref)))
    except StateError:
        lines.extend(("", "no turnout yet"))
    lines.extend(("", *bale_sheet(book, run.ref).render()))
    if book.runs.modules_in(run.ref):
        lines.extend(("", *allocation_sheet(book, run.ref).render()))
    return tuple(lines)
