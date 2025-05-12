"""One run open at a time, and feeding checks five things before it lets a module in."""

from __future__ import annotations

from datetime import date

import pytest

from ginstand.errors import NotFoundError, StateError
from ginstand.ginning.run import (
    close_run,
    current_run,
    feed,
    feed_all,
    open_run,
    require_open_run,
)
from ginstand.model.hold import HoldReason
from ginstand.store.book import Book
from ginstand.yard.holds import place
from ginstand.yard.receiving import receive

from .conftest import GIN, a_module

OPENED = date(2025, 10, 14)


def test_opening_a_run_files_it_under_the_crop_year_of_the_day(book: Book) -> None:
    run = open_run(book, "gr-1", GIN, OPENED, shift="day")
    assert run.ref == "GR-1"
    assert run.crop_year == 2025
    assert run.shift == "day"
    assert run.is_open


def test_a_january_run_still_belongs_to_the_autumn_crop_year(book: Book) -> None:
    assert open_run(book, "GR-9", GIN, date(2026, 1, 8)).crop_year == 2025


def test_a_second_open_run_is_refused_and_names_the_first(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    with pytest.raises(StateError, match="gin run GR-1 is still open"):
        open_run(book, "GR-2", GIN, OPENED)


def test_a_run_can_be_opened_once_the_last_one_closed(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    receive(book, a_module("M-1"))
    feed(book, "GR-1", "M-1", OPENED)
    close_run(book, "GR-1", OPENED)
    assert open_run(book, "GR-2", GIN, date(2025, 10, 15)).is_open


def test_feeding_hands_out_positions_in_order(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    receive(book, a_module("M-1"))
    receive(book, a_module("M-2"))
    assert feed(book, "GR-1", "M-1", OPENED) == 1
    assert feed(book, "GR-1", "M-2", OPENED) == 2


def test_a_closed_run_takes_nothing_more(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    receive(book, a_module("M-1"))
    receive(book, a_module("M-2"))
    feed(book, "GR-1", "M-1", OPENED)
    close_run(book, "GR-1", OPENED)
    with pytest.raises(StateError, match="gin run GR-1 closed on 2025-10-14"):
        feed(book, "GR-1", "M-2", OPENED)


def test_a_held_module_is_refused_with_the_reason(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    receive(book, a_module("M-1"))
    place(book, "M-1", HoldReason.PLASTIC, date(2025, 10, 3))
    with pytest.raises(StateError, match="held for plastic since 2025-10-03"):
        feed(book, "GR-1", "M-1", OPENED)


def test_a_module_already_ginned_names_the_run_it_went_on(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    receive(book, a_module("M-1"))
    feed(book, "GR-1", "M-1", OPENED)
    with pytest.raises(StateError, match="already ginned on run GR-1"):
        feed(book, "GR-1", "M-1", OPENED)


def test_a_module_not_yet_in_the_yard_is_refused(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    receive(book, a_module("M-1", received=date(2025, 10, 16)))
    with pytest.raises(StateError, match="not received until 2025-10-16"):
        feed(book, "GR-1", "M-1", OPENED)


def test_feeding_on_a_day_before_the_run_opened_is_refused(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    receive(book, a_module("M-1"))
    with pytest.raises(StateError, match="outside gin run GR-1"):
        feed(book, "GR-1", "M-1", date(2025, 10, 13))


def test_feeding_a_module_that_is_not_in_the_book_is_refused(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    with pytest.raises(NotFoundError, match="no module with reference M-9"):
        feed(book, "GR-1", "M-9", OPENED)


def test_feeding_a_queue_reports_what_went_in(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    for tag in ("M-1", "M-2", "M-3"):
        receive(book, a_module(tag))
    assert feed_all(book, "GR-1", ("m-3", "m-1", "m-2"), OPENED) == ("M-3", "M-1", "M-2")
    assert book.runs.modules_in("GR-1") == ("M-3", "M-1", "M-2")


def test_a_queue_that_hits_a_refusal_leaves_what_went_in_before_it(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    receive(book, a_module("M-1"))
    receive(book, a_module("M-2"))
    place(book, "M-2", HoldReason.WET, date(2025, 10, 3))
    with pytest.raises(StateError, match="held for wet"):
        feed_all(book, "GR-1", ("M-1", "M-2"), OPENED)
    assert book.runs.modules_in("GR-1") == ("M-1",)


def test_closing_an_empty_run_is_refused(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    with pytest.raises(StateError, match="has nothing in it"):
        close_run(book, "GR-1", OPENED)


def test_closing_a_closed_run_is_refused(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    receive(book, a_module("M-1"))
    feed(book, "GR-1", "M-1", OPENED)
    close_run(book, "GR-1", OPENED)
    with pytest.raises(StateError, match="closed on 2025-10-14"):
        close_run(book, "GR-1", OPENED)


def test_the_open_run_can_be_asked_for(book: Book) -> None:
    assert current_run(book) is None
    with pytest.raises(StateError, match="no gin run is open"):
        require_open_run(book)
    open_run(book, "GR-1", GIN, OPENED)
    assert require_open_run(book).ref == "GR-1"
