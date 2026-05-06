"""One season, start to finish, against an installed copy of this package.

The tests run against the source tree. This runs against whatever is installed,
which is the thing that catches a module left out of the wheel, an entry point
that does not resolve, and a package that imports fine and cannot open a book.

It is deliberately a whole season rather than a set of calls: producers in,
modules over the scale, a run ginned and closed, bales allocated, cards filed,
the loan worked out and a settlement issued. Every number it asserts is one a
gin office would notice being wrong.
"""

from __future__ import annotations

import sys
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

from ginstand.charges.published import seed_price_for, tariff_for
from ginstand.classing.filing import file_reading
from ginstand.classing.ingest import read
from ginstand.errors import GinstandError
from ginstand.ginning.allocate import allocate
from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.ginning.season import totals
from ginstand.ginning.seed import record_load
from ginstand.ginning.turnout import turnout_for
from ginstand.model.farm import Farm, Field
from ginstand.model.module import Module, ModuleKind, WrapKind
from ginstand.model.producer import Lease, LeaseKind, Producer
from ginstand.model.warehouse import Warehouse
from ginstand.settle.statement import settle
from ginstand.store.book import Book
from ginstand.warehouse.receipts import issue
from ginstand.yard.receiving import receive

OPENED = date(2025, 10, 14)
ISSUED = date(2025, 11, 3)


def _card(sequence: int) -> str:
    return f"2541207{sequence:05d}2025102231334045270810000         MEM "


def walk(path: Path) -> list[str]:
    """Run a season through the book at ``path`` and say what happened."""
    lines: list[str] = []
    with Book.create(path, date(2025, 8, 4)) as book:
        with book.writing() as writing:
            writing.producers.add(Producer(ref="P-12", name="Aldys Brothers", ccc_number="A4471"))
            writing.producers.add(Producer(ref="P-40", name="Merrick Land Co"))
            writing.leases.add(Lease(ref="L-1", tenant="P-12", kind=LeaseKind.OWNER))
            writing.leases.add(
                Lease(
                    ref="L-2",
                    tenant="P-12",
                    kind=LeaseKind.SHARE,
                    landlord="P-40",
                    landlord_share=Decimal("0.25"),
                )
            )
            writing.farms.add(Farm(ref="F-3", producer="P-12", name="Home Place"))
            writing.fields.add(
                Field(
                    ref="FL-9",
                    farm="F-3",
                    name="North 80",
                    acres=Decimal("78.4"),
                    lease="L-1",
                )
            )
            writing.fields.add(
                Field(
                    ref="FL-2",
                    farm="F-3",
                    name="Turnrow",
                    acres=Decimal("30"),
                    lease="L-2",
                )
            )
            writing.warehouses.add(Warehouse(ref="WH-1", name="Delta Compress", code="41-207"))
        lines.append("registers stood up")

        with book.writing() as writing:
            for tag, field_ref, net in (("M-1", "FL-9", 30_000), ("M-2", "FL-2", 20_000)):
                receive(
                    writing,
                    Module(
                        tag=tag,
                        field=field_ref,
                        kind=ModuleKind.RECTANGULAR,
                        harvested=date(2025, 9, 30),
                        received=date(2025, 10, 2),
                        gross_pounds=26_140 + net,
                        tare_pounds=26_140,
                        moisture_pct=Decimal("9.4"),
                        wrap=WrapKind.TARP,
                    ),
                )
        lines.append(f"{book.modules.count()} modules over the scale")

        with book.writing() as writing:
            open_run(writing, "GR-1", "41207", OPENED)
            feed(writing, "GR-1", "M-1", OPENED)
            feed(writing, "GR-1", "M-2", OPENED)
            for _ in range(34):
                press(writing, "GR-1", OPENED, 512, 22, Decimal("6.8"))
            record_load(writing, "GR-1", OPENED, 24_500)
            close_run(writing, "GR-1", OPENED)
            allocate(writing, "GR-1", OPENED)
        figure = turnout_for(book, "GR-1")
        lines.append(f"run closed at {figure.lint_turnout} turnout, {figure.bales} bales")

        cards = "\n".join(_card(n) for n in range(1, 35))
        with book.writing() as writing:
            filing = file_reading(writing, read(cards))
        lines.append(filing.summary)

        statement = settle(book, "GR-1", "P-12", tariff_for(2025), seed_price_for(2025), ISSUED)
        lines.append(
            f"statement {statement.share.bales} bales, total "
            f"{statement.total / 100:.2f}, {len(statement.splits)} leases"
        )

        with book.writing() as writing:
            receipt = issue(writing, "254120700001", "WH-1", date(2025, 10, 30))
        lines.append(f"receipt {receipt.number} issued to {receipt.holder}")

        season = totals(book, 2025)
        lines.append(f"season {season.bales} bales from {season.modules} modules")

        _expect(figure.bales == 34, "the run should have pressed 34 bales")
        _expect(filing.clean, "every card should have filed")
        _expect(statement.share.bales == 34, "P-12 fed everything so should hold it all")
        _expect(not statement.provisional, "every bale was classed")
        _expect(len(statement.splits) == 2, "P-12 farms under two leases")
        _expect(statement.total > 0, "this settlement should be positive")
        _expect(season.bales == 34, "the season should agree with the run")
    return lines


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise GinstandError(f"smoke walk: {message}")


def main() -> None:
    """Run the walk in a temporary book."""
    quiet = "--quiet" in sys.argv
    with tempfile.TemporaryDirectory() as folder:
        try:
            lines = walk(Path(folder) / "smoke.sqlite3")
        except GinstandError as exc:
            print(f"smoke: {exc}")
            sys.exit(1)
    if not quiet:
        for line in lines:
            print(f"  {line}")
    print("smoke: clean")


if __name__ == "__main__":
    main()
