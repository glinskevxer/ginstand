"""The two reports the yard runs every morning.

The standing shows what is out there and what order it should gin in. The hold
list shows what is not going anywhere and why, and it is a separate report on
purpose: a held module on the standing would be read as a queue position by
whoever is driving the loader.
"""

from __future__ import annotations

from datetime import date

from ginstand.report.table import Align, Column, Table
from ginstand.store.book import Book
from ginstand.units.weight import format_pounds
from ginstand.yard.holds import open_hold
from ginstand.yard.order import queue, yard_standing


def standing(book: Book, on: date) -> Table:
    """Every unginned module, worst first, with what is holding it."""
    rows = []
    for entry in yard_standing(book, on):
        hold = open_hold(book, entry.tag)
        rows.append(
            (
                entry.tag,
                entry.producer,
                entry.received.isoformat(),
                str(entry.days_in_yard),
                f"{entry.moisture_pct}%",
                str(entry.points),
                str(hold.reason) if hold is not None else ("at risk" if entry.at_risk else ""),
            )
        )
    total = sum(book.modules.get(entry.tag).net_pounds for entry in yard_standing(book, on))
    return Table(
        title=f"Module yard standing at {on.isoformat()}",
        columns=(
            Column("tag"),
            Column("producer"),
            Column("received"),
            Column("days", Align.RIGHT),
            Column("moisture", Align.RIGHT),
            Column("points", Align.RIGHT),
            Column("note"),
        ),
        rows=tuple(rows),
        footers=(("", "", "", "", format_pounds(total), "", ""),),
        empty_note="the yard is empty",
    )


def ginning_queue(book: Book, on: date, group: bool = True) -> Table:
    """The order the yard should feed, with the held modules left out."""
    tags = tuple(module.tag for module in book.modules.unginned())
    rows = []
    for position, tag in enumerate(queue(book, tags, on, group), start=1):
        module = book.modules.get(tag)
        rows.append(
            (
                str(position),
                tag,
                format_pounds(module.net_pounds),
                f"{module.moisture_pct}%",
            )
        )
    return Table(
        title=f"Ginning queue for {on.isoformat()}",
        columns=(
            Column("no", Align.RIGHT),
            Column("tag"),
            Column("seed cotton", Align.RIGHT),
            Column("moisture", Align.RIGHT),
        ),
        rows=tuple(rows),
        empty_note="nothing is free to gin",
    )


def holds(book: Book, on: date) -> Table:
    """Every module the yard is holding, oldest hold first."""
    rows = []
    for hold in book.holds.all_open():
        module = book.modules.get(hold.module)
        rows.append(
            (
                hold.module,
                str(hold.reason),
                hold.placed.isoformat(),
                str(hold.days_held(on)),
                hold.placed_by,
                format_pounds(module.net_pounds),
            )
        )
    return Table(
        title=f"Yard holds at {on.isoformat()}",
        columns=(
            Column("tag"),
            Column("reason"),
            Column("placed"),
            Column("days", Align.RIGHT),
            Column("by"),
            Column("seed cotton", Align.RIGHT),
        ),
        rows=tuple(rows),
        empty_note="nothing is held",
    )
