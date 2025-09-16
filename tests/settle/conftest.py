"""A book with two producers, three leases and a run ready to settle."""

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
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

OPENED = date(2025, 10, 14)
GIN = "41207"


@pytest.fixture
def book() -> Iterator[Book]:
    with Book.create(":memory:", date(2025, 8, 4)) as book:
        book.producers.add(Producer(ref="P-12", name="Aldys Brothers", ccc_number="A4471"))
        book.producers.add(Producer(ref="P-40", name="Merrick Land Co", ccc_number="M2210"))
        book.leases.add(Lease(ref="L-1", tenant="P-12", kind=LeaseKind.OWNER))
        book.leases.add(
            Lease(
                ref="L-2",
                tenant="P-12",
                kind=LeaseKind.SHARE,
                landlord="P-40",
                landlord_share=Decimal("0.25"),
            )
        )
        book.leases.add(Lease(ref="L-3", tenant="P-40", kind=LeaseKind.OWNER))
        book.farms.add(Farm(ref="F-3", producer="P-12", name="Home Place"))
        book.farms.add(Farm(ref="F-7", producer="P-40", name="River Place"))
        book.fields.add(
            Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("78.4"), lease="L-1")
        )
        book.fields.add(
            Field(ref="FL-2", farm="F-3", name="Turnrow", acres=Decimal("30"), lease="L-2")
        )
        book.fields.add(
            Field(ref="FL-5", farm="F-7", name="Bend", acres=Decimal("55"), lease="L-3")
        )
        yield book


def a_module(tag: str, field: str, net: int) -> Module:
    return Module(
        tag=tag,
        field=field,
        kind=ModuleKind.RECTANGULAR,
        harvested=date(2025, 9, 30),
        received=date(2025, 10, 2),
        gross_pounds=26_140 + net,
        tare_pounds=26_140,
        moisture_pct=Decimal("9.4"),
        wrap=WrapKind.TARP,
    )


def press_a_run(
    book: Book,
    feeds: tuple[tuple[str, str, int], ...] = (
        ("M-1", "FL-9", 20_000),
        ("M-2", "FL-2", 10_000),
        ("M-3", "FL-5", 10_000),
    ),
    bales: int = 8,
) -> None:
    """Open a run, feed it and press bales, leaving it open and unallocated."""
    open_run(book, "GR-1", GIN, OPENED)
    for tag, field, net in feeds:
        receive(book, a_module(tag, field, net))
        feed(book, "GR-1", tag, OPENED)
    for _ in range(bales):
        press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))


def gin_a_run(
    book: Book,
    feeds: tuple[tuple[str, str, int], ...] = (
        ("M-1", "FL-9", 20_000),
        ("M-2", "FL-2", 10_000),
        ("M-3", "FL-5", 10_000),
    ),
    bales: int = 8,
) -> None:
    """Press a run and take it through closing and allocation."""
    press_a_run(book, feeds, bales)
    close_run(book, "GR-1", OPENED)
    allocate(book, "GR-1", OPENED)
