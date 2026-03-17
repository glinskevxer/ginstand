"""Field yields, with a run's lint split between the fields that fed it."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import StateError
from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.report.field import best, yield_table, yields
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

from .conftest import a_module

OPENED = date(2025, 10, 14)


def gin(book: Book, feeds: tuple[tuple[str, str, int], ...], bales: int) -> None:
    open_run(book, "GR-1", "41207", OPENED)
    for tag, field_ref, net in feeds:
        receive(
            book,
            a_module(tag, field=field_ref, gross_pounds=26_140 + net, tare_pounds=26_140),
        )
        feed(book, "GR-1", tag, OPENED)
    for _ in range(bales):
        press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
    close_run(book, "GR-1", OPENED)


def test_a_crop_year_nobody_ginned_has_no_yields(book: Book) -> None:
    assert yields(book, 2025) == ()
    assert yield_table(book, 2025).render()[-1] == "no field fed a run in this crop year"
    with pytest.raises(StateError, match="no field fed a run in crop year 2025"):
        best(book, 2025)


def test_a_single_field_takes_the_whole_run(book: Book) -> None:
    gin(book, (("M-1", "FL-9", 20_000),), 14)
    found = yields(book, 2025)
    assert len(found) == 1
    assert found[0].field == "FL-9"
    assert found[0].seed_cotton_pounds == 20_000
    assert found[0].lint_pounds == 14 * 490


def test_a_run_s_lint_splits_between_the_fields_that_fed_it(book: Book) -> None:
    gin(book, (("M-1", "FL-9", 30_000), ("M-2", "FL-5", 10_000)), 20)
    found = {item.field: item for item in yields(book, 2025)}
    total = 20 * 490
    assert found["FL-9"].lint_pounds + found["FL-5"].lint_pounds == total
    assert found["FL-9"].lint_pounds == round(total * 0.75)


def test_the_per_acre_figures_use_the_field_s_own_acres(book: Book) -> None:
    gin(book, (("M-1", "FL-9", 20_000),), 14)
    item = yields(book, 2025)[0]
    assert item.acres == Decimal("78.40")
    assert item.lint_per_acre == Decimal("87.5")
    assert item.bales_per_acre == Decimal("0.18")


def test_the_turnout_is_off_the_field_s_own_seed_cotton(book: Book) -> None:
    gin(book, (("M-1", "FL-9", 20_000),), 14)
    assert yields(book, 2025)[0].turnout == Decimal("0.3430")


def test_the_best_field_is_the_one_with_most_lint_an_acre(book: Book) -> None:
    gin(book, (("M-1", "FL-9", 20_000), ("M-2", "FL-5", 20_000)), 28)
    top = best(book, 2025)
    assert top.field == "FL-5"
    assert [item.field for item in yields(book, 2025)] == ["FL-5", "FL-9"]


def test_a_field_that_fed_nothing_is_left_off(book: Book) -> None:
    gin(book, (("M-1", "FL-9", 20_000),), 14)
    assert [item.field for item in yields(book, 2025)] == ["FL-9"]


def test_an_open_run_is_counted_too(book: Book) -> None:
    open_run(book, "GR-1", "41207", OPENED)
    receive(book, a_module("M-1", field="FL-9", gross_pounds=46_140, tare_pounds=26_140))
    feed(book, "GR-1", "M-1", OPENED)
    press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
    assert yields(book, 2025)[0].lint_pounds == 490


def test_a_field_with_no_bales_yet_has_no_turnout(book: Book) -> None:
    open_run(book, "GR-1", "41207", OPENED)
    receive(book, a_module("M-1", field="FL-9", gross_pounds=46_140, tare_pounds=26_140))
    feed(book, "GR-1", "M-1", OPENED)
    item = yields(book, 2025)[0]
    assert item.lint_pounds == 0
    assert item.turnout == Decimal("0.0000")


def test_the_table_carries_the_variety_and_the_irrigation(book: Book) -> None:
    gin(book, (("M-1", "FL-9", 20_000),), 14)
    text = yield_table(book, 2025).text()
    assert "FL-9" in text
    assert "North 80" in text
    assert "lint/ac" in text
