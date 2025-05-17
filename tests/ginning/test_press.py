"""The bale number comes out of the book, and a closed run presses nothing."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import StateError
from ginstand.ginning.press import (
    average_bale_weight,
    bale_count,
    lint_off,
    next_tag,
    press,
)
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

from .conftest import GIN, a_module

OPENED = date(2025, 10, 14)


def stood_up(book: Book, ref: str = "GR-1", tags: tuple[str, ...] = ("M-1",)) -> None:
    open_run(book, ref, GIN, OPENED)
    for tag in tags:
        receive(book, a_module(tag))
        feed(book, ref, tag, OPENED)


def test_the_first_bale_of_a_crop_year_is_number_one(book: Book) -> None:
    stood_up(book)
    assert next_tag(book, "GR-1").sequence == 1
    bale = press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
    assert bale.tag == "254120700001"
    assert bale.sequence == 1


def test_the_numbers_run_on_across_runs_in_the_same_crop_year(book: Book) -> None:
    stood_up(book)
    press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
    press(book, "GR-1", OPENED, 508, 22, Decimal("6.9"))
    close_run(book, "GR-1", OPENED)
    open_run(book, "GR-2", GIN, date(2025, 10, 20))
    receive(book, a_module("M-2"))
    feed(book, "GR-2", "M-2", date(2025, 10, 20))
    assert next_tag(book, "GR-2").sequence == 3
    assert press(book, "GR-2", date(2025, 10, 20), 505, 21, Decimal("6.5")).sequence == 3


def test_a_new_crop_year_starts_the_numbers_again(book: Book) -> None:
    stood_up(book)
    press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
    close_run(book, "GR-1", OPENED)
    open_run(book, "GR-9", GIN, date(2026, 9, 8))
    receive(book, a_module("M-2", harvested=date(2026, 9, 1), received=date(2026, 9, 4)))
    feed(book, "GR-9", "M-2", date(2026, 9, 8))
    assert next_tag(book, "GR-9").tag == "264120700001"


def test_a_closed_run_presses_nothing(book: Book) -> None:
    stood_up(book)
    close_run(book, "GR-1", OPENED)
    with pytest.raises(StateError, match="so no bale can come off it"):
        press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))


def test_a_run_with_no_seed_cotton_presses_nothing(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    with pytest.raises(StateError, match="has no seed cotton in it yet"):
        press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))


def test_pressing_on_a_day_outside_the_run_is_refused(book: Book) -> None:
    stood_up(book)
    with pytest.raises(StateError, match="outside gin run GR-1"):
        press(book, "GR-1", date(2025, 10, 13), 512, 22, Decimal("6.8"))


def test_a_bale_above_the_storage_ceiling_is_refused_at_the_press(book: Book) -> None:
    stood_up(book)
    with pytest.raises(StateError, match="will heat in the warehouse"):
        press(book, "GR-1", OPENED, 512, 22, Decimal("7.6"))


def test_a_bale_exactly_on_the_ceiling_presses(book: Book) -> None:
    stood_up(book)
    assert press(book, "GR-1", OPENED, 512, 22, Decimal("7.5")).storable


def test_the_lint_off_a_run_adds_up_as_bales_come_off(book: Book) -> None:
    stood_up(book)
    assert lint_off(book, "GR-1") == 0
    press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
    press(book, "GR-1", OPENED, 498, 21, Decimal("6.9"))
    assert lint_off(book, "GR-1") == 490 + 477
    assert bale_count(book, "GR-1") == 2


def test_the_average_bale_weight_rounds_to_the_pound(book: Book) -> None:
    stood_up(book)
    press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
    press(book, "GR-1", OPENED, 498, 21, Decimal("6.9"))
    assert average_bale_weight(book, "GR-1") == 484


def test_a_run_with_no_bales_has_no_average(book: Book) -> None:
    stood_up(book)
    with pytest.raises(StateError, match="has pressed no bales"):
        average_bale_weight(book, "GR-1")


def test_the_press_records_which_stand_it_came_off(book: Book) -> None:
    stood_up(book)
    bale = press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"), stand="3")
    assert book.bales.get(bale.tag).stand == "3"
