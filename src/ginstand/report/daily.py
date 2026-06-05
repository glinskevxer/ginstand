"""The day sheet: everything that happened on one day, on one page.

This is the report the office runs last thing and pins on the wall. It is not a
summary of anything, it is a list of what was done, and the value of it is that
the numbers on it are the ones somebody can still remember.

Every section counts what it found and the sheet says so even when the count is
nothing. A day with no bales pressed is worth seeing on the sheet: it is either
a day the gin was down, which somebody knows about, or a day the pressing did
not get written down, which nobody does.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ginstand.report.table import Align, Column, Table
from ginstand.store.book import Book
from ginstand.units.weight import format_pounds


@dataclass(frozen=True, slots=True)
class Day:
    """What happened on one day."""

    day: date
    modules_in: tuple[str, ...]
    seed_cotton_in: int
    modules_ginned: tuple[str, ...]
    seed_cotton_ginned: int
    bales: tuple[str, ...]
    lint: int
    seed_out: int
    receipts: tuple[str, ...]
    cards: tuple[str, ...]
    holds_placed: tuple[str, ...]

    @property
    def quiet(self) -> bool:
        """Whether nothing at all was written down for this day."""
        return not (
            self.modules_in
            or self.modules_ginned
            or self.bales
            or self.receipts
            or self.cards
            or self.holds_placed
        )

    @property
    def lines(self) -> tuple[str, ...]:
        """The day sheet, as printed lines."""
        rows = [
            f"Day sheet for {self.day.isoformat()}",
            "",
            f"  weighed in     {len(self.modules_in):>4} modules  "
            f"{format_pounds(self.seed_cotton_in)}",
            f"  ginned         {len(self.modules_ginned):>4} modules  "
            f"{format_pounds(self.seed_cotton_ginned)}",
            f"  pressed        {len(self.bales):>4} bales    {format_pounds(self.lint)}",
            f"  seed out       {'':>4}           {format_pounds(self.seed_out)}",
            f"  receipted      {len(self.receipts):>4} bales",
            f"  cards filed    {len(self.cards):>4}",
            f"  holds placed   {len(self.holds_placed):>4}",
        ]
        if self.quiet:
            rows.append("")
            rows.append("  nothing was written down for this day")
        return tuple(rows)


def _seed_out(book: Book, day: date) -> int:
    row = book.connection.execute(
        "SELECT coalesce(sum(net_pounds), 0) AS net FROM seed_load WHERE weighed = ?",
        (day.isoformat(),),
    ).fetchone()
    return int(row["net"])


def _ginned(book: Book, day: date) -> tuple[tuple[str, ...], int]:
    rows = book.connection.execute(
        "SELECT r.module AS tag, m.gross_pounds - m.tare_pounds AS net"
        " FROM run_module r JOIN module m ON m.tag = r.module"
        " WHERE r.fed_on = ? ORDER BY r.run, r.position",
        (day.isoformat(),),
    ).fetchall()
    return tuple(str(row["tag"]) for row in rows), sum(int(row["net"]) for row in rows)


def sheet(book: Book, day: date) -> Day:
    """What happened on one day."""
    received = book.modules.received_on(day)
    ginned, ginned_pounds = _ginned(book, day)
    pressed = book.bales.pressed_on(day)
    cards = tuple(card.tag for card in book.cards.list_all() if card.classed == day)
    return Day(
        day=day,
        modules_in=tuple(module.tag for module in received),
        seed_cotton_in=sum(module.net_pounds for module in received),
        modules_ginned=ginned,
        seed_cotton_ginned=ginned_pounds,
        bales=tuple(bale.tag for bale in pressed),
        lint=sum(bale.net_pounds for bale in pressed),
        seed_out=_seed_out(book, day),
        receipts=tuple(item.number for item in book.receipts.issued_on(day)),
        cards=cards,
        holds_placed=tuple(hold.module for hold in book.holds.open_on(day) if hold.placed == day),
    )


def module_table(book: Book, day: date) -> Table:
    """The modules weighed in on a day."""
    rows = tuple(
        (
            module.tag,
            module.field,
            format_pounds(module.net_pounds),
            f"{module.moisture_pct}%",
            str(module.kind),
        )
        for module in book.modules.received_on(day)
    )
    total = sum(module.net_pounds for module in book.modules.received_on(day))
    return Table(
        title=f"Weighed in on {day.isoformat()}",
        columns=(
            Column("tag"),
            Column("field"),
            Column("seed cotton", Align.RIGHT),
            Column("moisture", Align.RIGHT),
            Column("kind"),
        ),
        rows=rows,
        footers=(("", "", format_pounds(total), "", ""),),
        empty_note="nothing crossed the scale",
    )


def bale_table(book: Book, day: date) -> Table:
    """The bales pressed on a day."""
    rows = tuple(
        (
            bale.tag,
            bale.run,
            format_pounds(bale.net_pounds),
            f"{bale.moisture_pct}%",
            bale.stand,
        )
        for bale in book.bales.pressed_on(day)
    )
    total = sum(bale.net_pounds for bale in book.bales.pressed_on(day))
    return Table(
        title=f"Pressed on {day.isoformat()}",
        columns=(
            Column("tag"),
            Column("run"),
            Column("net", Align.RIGHT),
            Column("moisture", Align.RIGHT),
            Column("stand"),
        ),
        rows=rows,
        footers=(("", "", format_pounds(total), "", ""),),
        empty_note="no bale came off the press",
    )


def full(book: Book, day: date) -> tuple[str, ...]:
    """The day sheet with the two lists under it."""
    return (
        *sheet(book, day).lines,
        "",
        *module_table(book, day).render(),
        "",
        *bale_table(book, day).render(),
    )
