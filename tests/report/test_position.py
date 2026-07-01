"""What is in store, priced against each bale's own crop year."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.ginning.allocate import allocate
from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.model.bale import Bale
from ginstand.model.ginrun import GinRun
from ginstand.model.warehouse import Warehouse
from ginstand.report.position import position_table, positions
from ginstand.store.book import Book
from ginstand.warehouse.receipts import issue, release, transfer
from ginstand.yard.receiving import receive

from .conftest import a_module

OPENED = date(2025, 10, 14)
ISSUED = date(2025, 10, 30)
ON = date(2026, 1, 30)


@pytest.fixture
def stored(book: Book) -> Book:
    book.warehouses.add(Warehouse(ref="WH-1", name="Delta Compress", code="41-207"))
    book.warehouses.add(Warehouse(ref="WH-2", name="Bend Compress", code="41-990"))
    open_run(book, "GR-1", "41207", OPENED)
    receive(book, a_module("M-1", gross_pounds=76_140, tare_pounds=26_140))
    feed(book, "GR-1", "M-1", OPENED)
    for _ in range(4):
        press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
    close_run(book, "GR-1", OPENED)
    allocate(book, "GR-1", OPENED)
    return book


def test_an_empty_warehouse_says_so(stored: Book) -> None:
    assert positions(stored, ON) == ()
    assert position_table(stored, ON).render()[-1] == "nothing is in store"


def test_a_position_counts_the_bales_and_the_weight(stored: Book) -> None:
    for sequence in (1, 2):
        issue(stored, f"2541207{sequence:05d}", "WH-1", ISSUED)
    found = positions(stored, ON)
    assert len(found) == 1
    assert found[0].warehouse == "WH-1"
    assert found[0].holder == "P-12"
    assert found[0].bales == 2
    assert found[0].net_pounds == 2 * 490


def test_the_storage_is_priced_and_added(stored: Book) -> None:
    issue(stored, "254120700001", "WH-1", ISSUED)
    assert positions(stored, ON)[0].owed > 0
    assert positions(stored, ON)[0].unpriced == 0


def test_a_holder_in_two_warehouses_is_two_positions(stored: Book) -> None:
    issue(stored, "254120700001", "WH-1", ISSUED)
    issue(stored, "254120700002", "WH-2", ISSUED)
    assert {item.warehouse for item in positions(stored, ON)} == {"WH-1", "WH-2"}


def test_two_holders_in_one_warehouse_are_two_positions(stored: Book) -> None:
    issue(stored, "254120700001", "WH-1", ISSUED)
    issue(stored, "254120700002", "WH-1", ISSUED)
    transfer(stored, "WR-00002", "P-40")
    holders = {item.holder for item in positions(stored, ON)}
    assert holders == {"P-12", "P-40"}


def test_the_biggest_position_is_listed_first(stored: Book) -> None:
    for sequence in (1, 2, 3):
        issue(stored, f"2541207{sequence:05d}", "WH-1", ISSUED)
    issue(stored, "254120700004", "WH-2", ISSUED)
    assert [item.warehouse for item in positions(stored, ON)] == ["WH-1", "WH-2"]


def test_a_released_bale_is_out_of_the_position(stored: Book) -> None:
    issue(stored, "254120700001", "WH-1", ISSUED)
    issue(stored, "254120700002", "WH-1", ISSUED)
    release(stored, "WR-00001", date(2025, 12, 1))
    assert positions(stored, ON)[0].bales == 1


def test_a_receipt_issued_after_the_day_is_left_out(stored: Book) -> None:
    issue(stored, "254120700001", "WH-1", date(2026, 3, 1))
    assert positions(stored, ON) == ()


def test_the_oldest_receipt_is_carried(stored: Book) -> None:
    issue(stored, "254120700001", "WH-1", date(2025, 12, 1))
    issue(stored, "254120700002", "WH-1", ISSUED)
    assert positions(stored, ON)[0].oldest == ISSUED


def test_a_bale_with_no_contract_for_its_year_is_counted_not_priced(
    stored: Book,
) -> None:
    """No storage contract is published for 2019, and a bale can still be in store."""
    old = date(2019, 10, 14)
    stored.runs.add(GinRun(ref="GR-9", crop_year=2019, gin_code="41207", opened=old))
    stored.bales.add(
        Bale(
            tag="194120700001",
            run="GR-9",
            pressed=old,
            gross_pounds=512,
            tare_pounds=22,
            moisture_pct=Decimal("6.8"),
        )
    )
    stored.allocations.assign("194120700001", "P-12", "GR-9", old)
    issue(stored, "194120700001", "WH-1", date(2019, 10, 30))
    found = positions(stored, ON)
    assert found[0].unpriced == 1
    assert found[0].owed == 0
    assert "unpriced" in found[0].line


def test_the_table_totals_the_bales_and_the_money(stored: Book) -> None:
    for sequence in (1, 2):
        issue(stored, f"2541207{sequence:05d}", "WH-1", ISSUED)
    text = position_table(stored, ON).text()
    assert "WH-1" in text
    assert "980" in text
