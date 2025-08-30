"""The minimum is a floor under the days charged, not under the bill."""

from __future__ import annotations

from datetime import date

import pytest

from ginstand.errors import ValidationError
from ginstand.store.book import Book
from ginstand.units.money import format_money, money
from ginstand.warehouse.receipts import issue, release
from ginstand.warehouse.storage import (
    StorageTariff,
    bill_holder,
    bill_receipt,
    total_for_holder,
)

from .conftest import gin_a_run

ISSUED = date(2025, 10, 30)

TARIFF = StorageTariff(
    receiving=money("3.10"),
    per_day=money("0.08"),
    load_out=money("2.40"),
    free_days=10,
    minimum_days=60,
)


def test_a_stay_inside_the_free_period_is_not_charged_for_storage() -> None:
    assert TARIFF.chargeable_days(0) == 0
    assert TARIFF.chargeable_days(10) == 0


def test_a_stay_inside_the_minimum_is_charged_the_minimum_less_the_free_days() -> None:
    assert TARIFF.chargeable_days(12) == 50
    assert TARIFF.chargeable_days(59) == 50
    assert TARIFF.chargeable_days(60) == 50


def test_a_stay_past_the_minimum_is_charged_the_days_it_actually_was() -> None:
    assert TARIFF.chargeable_days(90) == 80
    assert TARIFF.chargeable_days(200) == 190


def test_a_tariff_with_no_free_period_or_minimum_charges_the_days() -> None:
    plain = StorageTariff(receiving=money("0"), per_day=money("0.08"), load_out=money("0"))
    assert plain.chargeable_days(12) == 12
    assert plain.chargeable_days(0) == 0


def test_a_negative_stay_is_refused() -> None:
    with pytest.raises(ValidationError, match="must not be negative"):
        TARIFF.chargeable_days(-1)


def test_a_free_period_longer_than_the_minimum_is_a_contradiction() -> None:
    with pytest.raises(ValidationError, match="can never be charged"):
        StorageTariff(
            receiving=money("0"),
            per_day=money("0.08"),
            load_out=money("0"),
            free_days=90,
            minimum_days=60,
        )


def test_a_negative_rate_is_refused() -> None:
    with pytest.raises(ValidationError, match="must not be negative"):
        StorageTariff(receiving=money("-1"), per_day=money("0.08"), load_out=money("0"))


def test_a_bale_still_in_store_is_not_charged_load_out(book: Book) -> None:
    gin_a_run(book)
    receipt = issue(book, "254120700001", "WH-1", ISSUED)
    bill = bill_receipt(TARIFF, receipt, date(2026, 1, 30))
    assert bill.days_stored == 92
    assert bill.chargeable_days == 82
    assert bill.load_out == 0
    assert bill.receiving == money("3.10")
    assert bill.storage == money("6.56")
    assert format_money(bill.total) == "$9.66"


def test_a_released_bale_is_charged_load_out(book: Book) -> None:
    gin_a_run(book)
    issue(book, "254120700001", "WH-1", ISSUED)
    released = release(book, "WR-00001", date(2026, 1, 30))
    bill = bill_receipt(TARIFF, released, date(2026, 5, 1))
    assert bill.days_stored == 92
    assert bill.load_out == money("2.40")
    assert format_money(bill.total) == "$12.06"


def test_a_bale_pulled_early_still_pays_the_minimum(book: Book) -> None:
    gin_a_run(book)
    issue(book, "254120700001", "WH-1", ISSUED)
    released = release(book, "WR-00001", date(2025, 11, 11))
    bill = bill_receipt(TARIFF, released, date(2026, 5, 1))
    assert bill.days_stored == 12
    assert bill.chargeable_days == 50
    assert bill.storage == money("4.00")


def test_every_receipt_a_holder_has_is_billed(book: Book) -> None:
    gin_a_run(book)
    for tag in ("254120700001", "254120700002"):
        issue(book, tag, "WH-1", ISSUED)
    bills = bill_holder(book, TARIFF, "P-12", date(2026, 1, 30))
    assert len(bills) == 2
    assert total_for_holder(book, TARIFF, "P-12", date(2026, 1, 30)) == money("19.32")


def test_a_receipt_issued_after_the_billing_day_is_left_out(book: Book) -> None:
    gin_a_run(book)
    issue(book, "254120700001", "WH-1", ISSUED)
    issue(book, "254120700002", "WH-1", date(2026, 2, 1))
    bills = bill_holder(book, TARIFF, "P-12", date(2026, 1, 30))
    assert [bill.tag for bill in bills] == ["254120700001"]


def test_a_holder_with_nothing_in_store_owes_nothing(book: Book) -> None:
    gin_a_run(book)
    assert bill_holder(book, TARIFF, "P-40", date(2026, 1, 30)) == ()
    assert total_for_holder(book, TARIFF, "P-40", date(2026, 1, 30)) == 0


def test_the_bill_line_shows_both_day_counts(book: Book) -> None:
    gin_a_run(book)
    receipt = issue(book, "254120700001", "WH-1", ISSUED)
    bill = bill_receipt(TARIFF, receipt, date(2025, 11, 11))
    assert bill.line == "WR-00001  254120700001  12 days (50 charged)  $7.10"
