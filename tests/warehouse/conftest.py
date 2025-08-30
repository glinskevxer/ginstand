"""A book with a run ginned, allocated and ready to ship."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest

from ginstand.ginning.allocate import allocate
from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.model.farm import Farm, Field
from ginstand.model.module import Module, ModuleKind, WrapKind
from ginstand.model.producer import Lease, LeaseKind, Producer
from ginstand.model.warehouse import Warehouse
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

OPENED = date(2025, 10, 14)
GIN = "41207"


@pytest.fixture
def book() -> Iterator[Book]:
    with Book.create(":memory:", date(2025, 8, 4)) as book:
        book.producers.add(Producer(ref="P-12", name="Aldys Brothers", ccc_number="A4471"))
        book.producers.add(Producer(ref="P-40", name="Merrick Land Co"))
        book.leases.add(Lease(ref="L-1", tenant="P-12", kind=LeaseKind.OWNER))
        book.farms.add(Farm(ref="F-3", producer="P-12", name="Home Place"))
        book.fields.add(
            Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("78.4"), lease="L-1")
        )
        book.warehouses.add(Warehouse(ref="WH-1", name="Delta Compress", code="41-207"))
        yield book


def press_a_run(book: Book, bales: int = 3, moisture: str = "6.8") -> None:
    """Open a run, feed it, press bales, and leave it open and unallocated."""
    open_run(book, "GR-1", GIN, OPENED)
    receive(
        book,
        Module(
            tag="M-1",
            field="FL-9",
            kind=ModuleKind.RECTANGULAR,
            harvested=date(2025, 9, 30),
            received=date(2025, 10, 2),
            gross_pounds=56_140,
            tare_pounds=26_140,
            moisture_pct=Decimal("9.4"),
            wrap=WrapKind.TARP,
        ),
    )
    feed(book, "GR-1", "M-1", OPENED)
    for _ in range(bales):
        press(book, "GR-1", OPENED, 512, 22, Decimal(moisture))


def gin_a_run(book: Book, bales: int = 3, moisture: str = "6.8") -> None:
    """Press a run and take it all the way through closing and allocation."""
    press_a_run(book, bales, moisture)
    close_run(book, "GR-1", OPENED)
    allocate(book, "GR-1", OPENED)
