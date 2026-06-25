"""One search across every register, because the caller has a piece of paper."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import ValidationError
from ginstand.ginning.allocate import allocate
from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.model.instrument import Instrument, InstrumentKind
from ginstand.model.warehouse import Warehouse
from ginstand.report.find import MINIMUM_SEARCH, SHOWN, result_table, search
from ginstand.store.book import Book
from ginstand.warehouse.receipts import issue
from ginstand.yard.receiving import receive

from .conftest import a_module

OPENED = date(2025, 10, 14)


@pytest.fixture
def stocked(book: Book) -> Book:
    open_run(book, "GR-1", "41207", OPENED)
    receive(book, a_module("M-4471", gross_pounds=46_140, tare_pounds=26_140))
    feed(book, "GR-1", "M-4471", OPENED)
    for _ in range(3):
        press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
    close_run(book, "GR-1", OPENED)
    allocate(book, "GR-1", OPENED)
    book.warehouses.add(Warehouse(ref="WH-1", name="Delta Compress", code="41-207"))
    issue(book, "254120700001", "WH-1", date(2025, 10, 30))
    book.instruments.add(
        Instrument(ref="SC-1", kind=InstrumentKind.TRUCK_SCALE, description="Weighbridge")
    )
    return book


def test_a_search_that_is_too_short_is_refused(stocked: Book) -> None:
    with pytest.raises(ValidationError, match=f"at least {MINIMUM_SEARCH} characters"):
        search(stocked, "P")


def test_a_producer_is_found_by_reference_or_name(stocked: Book) -> None:
    assert [hit.kind for hit in search(stocked, "P-12")] == ["producer"]
    assert [hit.reference for hit in search(stocked, "aldys")] == ["P-12"]


def test_a_field_is_found_by_its_name(stocked: Book) -> None:
    found = search(stocked, "north")
    assert [hit.kind for hit in found] == ["field"]
    assert "78.40 acres" in found[0].description


def test_a_module_is_found_by_part_of_its_tag(stocked: Book) -> None:
    found = search(stocked, "4471")
    assert any(hit.kind == "module" for hit in found)


def test_a_bale_is_found_by_the_last_digits_on_the_paper(stocked: Book) -> None:
    found = [hit for hit in search(stocked, "00002") if hit.kind == "bale"]
    assert len(found) == 1
    assert "P-12" in found[0].description


def test_a_receipt_is_found_by_its_number_or_its_bale(stocked: Book) -> None:
    by_number = [hit for hit in search(stocked, "WR-00001") if hit.kind == "receipt"]
    assert by_number
    assert "outstanding" in by_number[0].description
    by_bale = [hit for hit in search(stocked, "254120700001") if hit.kind == "receipt"]
    assert by_bale


def test_a_run_is_found_and_says_whether_it_is_open(stocked: Book) -> None:
    found = [hit for hit in search(stocked, "GR-1") if hit.kind == "gin run"]
    assert "closed 2025-10-14" in found[0].description


def test_a_warehouse_and_an_instrument_are_searched_too(stocked: Book) -> None:
    assert [hit.kind for hit in search(stocked, "delta")] == ["warehouse"]
    assert [hit.kind for hit in search(stocked, "weighbridge")] == ["instrument"]


def test_the_search_is_not_case_sensitive(stocked: Book) -> None:
    assert search(stocked, "p-12") == search(stocked, "P-12")


def test_something_nobody_has_is_found_nowhere(stocked: Book) -> None:
    assert search(stocked, "ZZZZ") == ()
    assert result_table(stocked, "ZZZZ").render()[-1] == "nothing in the book carries that"


def test_the_table_says_how_many_it_found(stocked: Book) -> None:
    text = result_table(stocked, "254120").text()
    assert "4 found" in text


def test_a_wide_search_is_capped_and_says_so(book: Book) -> None:
    open_run(book, "GR-1", "41207", OPENED)
    receive(book, a_module("M-1", gross_pounds=76_140, tare_pounds=26_140))
    feed(book, "GR-1", "M-1", OPENED)
    for _ in range(SHOWN + 5):
        press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
    found = search(book, "2541207")
    assert len(found) > SHOWN
    table = result_table(book, "2541207")
    assert f"showing {SHOWN}" in table.render()[0]
    assert len(table.rows) == SHOWN


def test_the_hit_line_reads_as_one_row(stocked: Book) -> None:
    hit = search(stocked, "P-12")[0]
    assert hit.line.startswith("producer   P-12")
