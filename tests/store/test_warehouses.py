"""One receipt per bale, kept true by a unique index on the tag."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.model.bale import Bale
from ginstand.model.ginrun import GinRun
from ginstand.model.producer import Producer
from ginstand.model.warehouse import Receipt, Warehouse
from ginstand.store.bales import BaleStore
from ginstand.store.growers import ProducerStore
from ginstand.store.runs import RunStore
from ginstand.store.warehouses import ReceiptStore, WarehouseStore

PRESSED = date(2025, 10, 14)
ISSUED = date(2025, 10, 30)


@pytest.fixture
def shipped(book: sqlite3.Connection) -> sqlite3.Connection:
    ProducerStore(book).add(Producer(ref="P-12", name="Aldys Brothers"))
    ProducerStore(book).add(Producer(ref="P-40", name="Merrick Land Co"))
    RunStore(book).add(GinRun(ref="GR-1", crop_year=2025, gin_code="41207", opened=PRESSED))
    bales = BaleStore(book)
    for sequence in (61, 62, 63):
        bales.add(
            Bale(
                tag=f"2541207{sequence:05d}",
                run="GR-1",
                pressed=PRESSED,
                gross_pounds=512,
                tare_pounds=22,
                moisture_pct=Decimal("6.8"),
            )
        )
    WarehouseStore(book).add(Warehouse(ref="WH-1", name="Delta Compress", code="41-207"))
    WarehouseStore(book).add(Warehouse(ref="WH-2", name="Gin yard shed"))
    return book


def a_receipt(number: str, sequence: int = 61, **changes: object) -> Receipt:
    fields: dict[str, object] = {
        "number": number,
        "tag": f"2541207{sequence:05d}",
        "warehouse": "WH-1",
        "holder": "P-12",
        "issued": ISSUED,
    }
    fields.update(changes)
    return Receipt(**fields)  # type: ignore[arg-type]


def test_a_warehouse_reads_back_whole(shipped: sqlite3.Connection) -> None:
    house = WarehouseStore(shipped).get("wh-1")
    assert house.name == "Delta Compress"
    assert house.licensed


def test_only_licensed_warehouses_come_back_from_the_licensed_list(
    shipped: sqlite3.Connection,
) -> None:
    assert [h.ref for h in WarehouseStore(shipped).licensed()] == ["WH-1"]


def test_adding_and_updating_a_warehouse_follow_the_usual_rules(
    shipped: sqlite3.Connection,
) -> None:
    store = WarehouseStore(shipped)
    with pytest.raises(DuplicateError):
        store.add(Warehouse(ref="WH-1", name="Somewhere else"))
    store.update(Warehouse(ref="WH-2", name="Gin yard shed", code="41-990"))
    assert store.get("WH-2").licensed
    with pytest.raises(NotFoundError):
        store.update(Warehouse(ref="WH-9", name="Nowhere"))


def test_a_receipt_reads_back_whole(shipped: sqlite3.Connection) -> None:
    store = ReceiptStore(shipped)
    receipt = a_receipt("WR-10041", note="first of the season")
    store.add(receipt)
    assert store.get("wr-10041") == receipt


def test_a_second_receipt_against_the_same_bale_is_refused(
    shipped: sqlite3.Connection,
) -> None:
    store = ReceiptStore(shipped)
    store.add(a_receipt("WR-10041"))
    with pytest.raises(sqlite3.IntegrityError):
        store.add(a_receipt("WR-10042"))


def test_a_receipt_number_cannot_be_used_twice(shipped: sqlite3.Connection) -> None:
    store = ReceiptStore(shipped)
    store.add(a_receipt("WR-10041"))
    with pytest.raises(DuplicateError, match="receipt WR-10041"):
        store.add(a_receipt("WR-10041", sequence=62))


def test_a_receipt_for_a_bale_nobody_pressed_is_refused(
    shipped: sqlite3.Connection,
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        ReceiptStore(shipped).add(a_receipt("WR-10041", sequence=999))


def test_the_receipt_against_a_bale_can_be_looked_up(shipped: sqlite3.Connection) -> None:
    store = ReceiptStore(shipped)
    assert store.for_bale("254120700061") is None
    store.add(a_receipt("WR-10041"))
    found = store.for_bale("25-41207-00061")
    assert found is not None
    assert found.number == "WR-10041"


def test_releasing_a_receipt_writes_through(shipped: sqlite3.Connection) -> None:
    store = ReceiptStore(shipped)
    store.add(a_receipt("WR-10041"))
    store.save(store.get("WR-10041").release_on(date(2026, 2, 10)))
    assert not store.get("WR-10041").outstanding
    assert store.outstanding() == ()


def test_saving_a_receipt_that_was_never_issued_is_refused(
    shipped: sqlite3.Connection,
) -> None:
    with pytest.raises(NotFoundError, match="no receipt with reference WR-9"):
        ReceiptStore(shipped).save(a_receipt("WR-9"))


def test_receipts_list_by_holder_and_by_warehouse(shipped: sqlite3.Connection) -> None:
    store = ReceiptStore(shipped)
    store.add(a_receipt("WR-10041", 61, holder="P-12"))
    store.add(a_receipt("WR-10042", 62, holder="P-40"))
    store.add(a_receipt("WR-10043", 63, holder="P-12", warehouse="WH-2"))
    assert [r.number for r in store.for_holder("P-12")] == ["WR-10041", "WR-10043"]
    assert [r.number for r in store.in_warehouse("WH-1")] == ["WR-10041", "WR-10042"]


def test_a_released_receipt_drops_out_of_the_outstanding_lists(
    shipped: sqlite3.Connection,
) -> None:
    store = ReceiptStore(shipped)
    store.add(a_receipt("WR-10041", 61))
    store.add(a_receipt("WR-10042", 62))
    store.save(store.get("WR-10041").release_on(date(2026, 2, 10)))
    assert [r.number for r in store.outstanding()] == ["WR-10042"]
    assert [r.number for r in store.outstanding_for("P-12")] == ["WR-10042"]
    assert len(store.for_holder("P-12")) == 2


def test_receipts_list_for_a_day(shipped: sqlite3.Connection) -> None:
    store = ReceiptStore(shipped)
    store.add(a_receipt("WR-10041", 61))
    store.add(a_receipt("WR-10042", 62, issued=date(2025, 11, 4)))
    assert [r.number for r in store.issued_on(ISSUED)] == ["WR-10041"]
