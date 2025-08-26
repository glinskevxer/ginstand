"""A receipt is a document of title, so it names a holder of its own."""

from __future__ import annotations

from datetime import date

import pytest

from ginstand.errors import ValidationError
from ginstand.model.warehouse import Receipt, Warehouse

ISSUED = date(2025, 10, 30)


def a_receipt(**changes: object) -> Receipt:
    fields: dict[str, object] = {
        "number": "wr-10041",
        "tag": "254120700061",
        "warehouse": "wh-1",
        "holder": "p-12",
        "issued": ISSUED,
    }
    fields.update(changes)
    return Receipt(**fields)  # type: ignore[arg-type]


def test_a_warehouse_normalises_its_reference_and_code() -> None:
    house = Warehouse(ref=" wh-1 ", name="  Delta Compress  ", code=" 41-207 ")
    assert house.ref == "WH-1"
    assert house.name == "Delta Compress"
    assert house.code == "41-207"
    assert house.licensed


def test_a_warehouse_without_a_code_cannot_back_a_loan() -> None:
    assert not Warehouse(ref="WH-2", name="Gin yard shed").licensed


def test_a_warehouse_without_a_name_is_refused() -> None:
    with pytest.raises(ValidationError, match="warehouse name: is empty"):
        Warehouse(ref="WH-1", name="  ")


def test_a_receipt_normalises_every_reference_on_it() -> None:
    receipt = a_receipt(tag="25-41207-00061")
    assert receipt.number == "WR-10041"
    assert receipt.tag == "254120700061"
    assert receipt.warehouse == "WH-1"
    assert receipt.holder == "P-12"


def test_a_new_receipt_is_outstanding() -> None:
    assert a_receipt().outstanding


def test_releasing_gives_back_a_released_receipt() -> None:
    receipt = a_receipt()
    released = receipt.release_on(date(2026, 2, 10))
    assert receipt.outstanding
    assert not released.outstanding
    assert released.released == date(2026, 2, 10)


def test_releasing_twice_names_the_day_it_was_released() -> None:
    released = a_receipt(released=date(2026, 2, 10))
    with pytest.raises(ValidationError, match="was released on 2026-02-10"):
        released.release_on(date(2026, 3, 1))


def test_a_receipt_released_before_it_was_issued_is_refused() -> None:
    with pytest.raises(ValidationError, match="before the receipt was issued"):
        a_receipt(released=date(2025, 10, 29))


def test_days_stored_counts_to_today_while_it_is_outstanding() -> None:
    assert a_receipt().days_stored(date(2025, 11, 30)) == 31
    assert a_receipt().days_stored(ISSUED) == 0


def test_days_stored_stops_at_the_release() -> None:
    released = a_receipt(released=date(2025, 11, 30))
    assert released.days_stored(date(2026, 5, 1)) == 31


def test_asking_before_it_was_issued_is_refused() -> None:
    with pytest.raises(ValidationError, match="before the receipt was issued"):
        a_receipt().days_stored(date(2025, 10, 1))


def test_transferring_changes_the_holder_and_nothing_else() -> None:
    receipt = a_receipt()
    moved = receipt.transfer_to("p-40")
    assert moved.holder == "P-40"
    assert moved.number == receipt.number
    assert moved.tag == receipt.tag
    assert moved.issued == receipt.issued
    assert moved.outstanding


def test_a_released_receipt_cannot_be_transferred() -> None:
    released = a_receipt(released=date(2026, 2, 10))
    with pytest.raises(ValidationError, match="has been released"):
        released.transfer_to("P-40")


def test_a_receipt_is_frozen() -> None:
    receipt = a_receipt()
    with pytest.raises(AttributeError):
        receipt.holder = "P-40"  # type: ignore[misc]
