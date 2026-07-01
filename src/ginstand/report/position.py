"""What is in store, whose it is, and what it is costing to keep.

The gin does not own the cotton in the warehouse and it still has to be able to
say where all of it is, because it issued the receipts. So the position is by
warehouse first, which is where a lorry goes, and by holder second, which is who
gets the bill.

Storage is priced against the crop year's contract, so a position across two
crop years prices each bale against its own year. That is the only way it can
be done and it is worth saying out loud, because the obvious implementation
prices everything against this year's contract and is wrong by a few cents a
bale on last year's cotton.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ginstand.charges.published import storage_for
from ginstand.errors import ScheduleError
from ginstand.report.table import Align, Column, Table
from ginstand.store.book import Book
from ginstand.units.money import Money, format_money
from ginstand.units.weight import format_pounds
from ginstand.warehouse.storage import bill_receipt


@dataclass(frozen=True, slots=True)
class Position:
    """What one holder has in one warehouse."""

    warehouse: str
    holder: str
    bales: int
    net_pounds: int
    oldest: date
    owed: Money
    unpriced: int

    @property
    def line(self) -> str:
        """The line the position prints."""
        note = f", {self.unpriced} unpriced" if self.unpriced else ""
        return (
            f"{self.warehouse}  {self.holder}  {self.bales} bales  "
            f"{format_pounds(self.net_pounds)}  {format_money(self.owed)}{note}"
        )


@dataclass
class _Running:
    """What has been counted so far for one warehouse and holder."""

    bales: int = 0
    net_pounds: int = 0
    oldest: date | None = None
    owed: Money = field(default_factory=lambda: Money(0))
    unpriced: int = 0


def positions(book: Book, on: date) -> tuple[Position, ...]:
    """Every holder's position in every warehouse, most bales first.

    A bale whose crop year has no storage contract published is counted and left
    out of the money, rather than priced against a year it did not sit in.
    """
    gathered: dict[tuple[str, str], _Running] = {}
    for receipt in book.receipts.outstanding():
        if receipt.issued > on:
            continue
        bale = book.bales.get(receipt.tag)
        running = gathered.setdefault((receipt.warehouse, receipt.holder), _Running())
        running.bales += 1
        running.net_pounds += bale.net_pounds
        running.oldest = (
            receipt.issued if running.oldest is None else min(running.oldest, receipt.issued)
        )
        try:
            contract = storage_for(bale.crop_year)
        except ScheduleError:
            running.unpriced += 1
            continue
        running.owed = Money(running.owed + bill_receipt(contract, receipt, on).total)

    built = [
        Position(
            warehouse=warehouse,
            holder=holder,
            bales=running.bales,
            net_pounds=running.net_pounds,
            oldest=running.oldest or on,
            owed=running.owed,
            unpriced=running.unpriced,
        )
        for (warehouse, holder), running in gathered.items()
    ]
    return tuple(sorted(built, key=lambda item: (-item.bales, item.warehouse, item.holder)))


def position_table(book: Book, on: date) -> Table:
    """The whole position, most bales first."""
    found = positions(book, on)
    rows = tuple(
        (
            item.warehouse,
            item.holder,
            str(item.bales),
            f"{item.net_pounds:,}",
            item.oldest.isoformat(),
            format_money(item.owed),
            str(item.unpriced) if item.unpriced else "",
        )
        for item in found
    )
    return Table(
        title=f"In store at {on.isoformat()}",
        columns=(
            Column("warehouse"),
            Column("holder"),
            Column("bales", Align.RIGHT),
            Column("net", Align.RIGHT),
            Column("oldest"),
            Column("storage", Align.RIGHT),
            Column("unpriced", Align.RIGHT),
        ),
        rows=rows,
        footers=(
            (
                "",
                "",
                str(sum(item.bales for item in found)),
                f"{sum(item.net_pounds for item in found):,}",
                "",
                format_money(Money(sum(item.owed for item in found))),
                "",
            ),
        ),
        empty_note="nothing is in store",
    )
