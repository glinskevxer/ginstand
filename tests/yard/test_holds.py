"""Holds refuse what should not be held, and say what is in the way."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import NotFoundError, StateError
from ginstand.model.ginrun import GinRun
from ginstand.model.hold import HoldReason
from ginstand.store.book import Book
from ginstand.yard.holds import (
    HOLD_MOISTURE,
    blocked,
    free_to_gin,
    held,
    lift,
    open_hold,
    place,
    suggest,
)
from ginstand.yard.receiving import receive

from .conftest import a_module

PLACED = date(2025, 10, 3)


def test_a_module_is_free_to_gin_until_something_holds_it(book: Book) -> None:
    receive(book, a_module("M-1"))
    assert not held(book, "M-1")
    assert open_hold(book, "M-1") is None


def test_placing_a_hold_records_who_placed_it(book: Book) -> None:
    receive(book, a_module("M-1"))
    hold = place(book, "m-1", HoldReason.PLASTIC, PLACED, "R Ellis", "wrap torn")
    assert hold.module == "M-1"
    assert hold.placed_by == "R Ellis"
    assert hold.note == "wrap torn"
    assert held(book, "M-1")


def test_a_second_hold_names_the_one_in_the_way(book: Book) -> None:
    receive(book, a_module("M-1"))
    place(book, "M-1", HoldReason.WET, PLACED)
    with pytest.raises(StateError, match="already held for wet since 2025-10-03"):
        place(book, "M-1", HoldReason.PLASTIC, date(2025, 10, 5))


def test_a_module_that_has_been_ginned_cannot_be_held(book: Book) -> None:
    receive(book, a_module("M-1"))
    book.runs.add(GinRun(ref="GR-1", crop_year=2025, gin_code="41207", opened=date(2025, 10, 4)))
    book.runs.feed("GR-1", "M-1", date(2025, 10, 4))
    with pytest.raises(StateError, match="already been ginned on run GR-1"):
        place(book, "M-1", HoldReason.WEIGHT, date(2025, 10, 5))


def test_a_hold_before_the_module_arrived_is_refused(book: Book) -> None:
    receive(book, a_module("M-1", received=date(2025, 10, 2)))
    with pytest.raises(StateError, match="before module M-1 was received"):
        place(book, "M-1", HoldReason.WET, date(2025, 10, 1))


def test_holding_a_module_nobody_weighed_is_refused(book: Book) -> None:
    with pytest.raises(NotFoundError, match="no module with reference M-9"):
        place(book, "M-9", HoldReason.WET, PLACED)


def test_lifting_frees_the_module(book: Book) -> None:
    receive(book, a_module("M-1"))
    place(book, "M-1", HoldReason.WET, PLACED)
    lifted = lift(book, "M-1", date(2025, 10, 7), "J Pryor")
    assert not lifted.open
    assert lifted.lifted_by == "J Pryor"
    assert not held(book, "M-1")


def test_lifting_a_module_that_is_not_held_is_refused(book: Book) -> None:
    receive(book, a_module("M-1"))
    with pytest.raises(StateError, match="module M-1 is not held"):
        lift(book, "M-1", date(2025, 10, 7))


def test_a_module_can_be_held_again_after_a_lift(book: Book) -> None:
    receive(book, a_module("M-1"))
    place(book, "M-1", HoldReason.WET, PLACED)
    lift(book, "M-1", date(2025, 10, 7))
    again = place(book, "M-1", HoldReason.WEIGHT, date(2025, 10, 9))
    assert again.open
    assert len(book.holds.history_for("M-1")) == 2


def test_the_ticket_suggests_a_wet_hold_past_the_dryers(book: Book) -> None:
    assert suggest(a_module("M-1", moisture_pct=HOLD_MOISTURE)) is HoldReason.WET
    assert suggest(a_module("M-1", moisture_pct=Decimal("18.0"))) is HoldReason.WET


def test_the_ticket_suggests_nothing_for_a_module_that_can_go_through(book: Book) -> None:
    assert suggest(a_module("M-1", moisture_pct=Decimal("13.9"))) is None
    assert suggest(a_module("M-1", moisture_pct=Decimal("7.0"))) is None


def test_the_free_list_keeps_the_order_it_was_given(book: Book) -> None:
    for tag in ("M-1", "M-2", "M-3"):
        receive(book, a_module(tag))
    place(book, "M-2", HoldReason.WET, PLACED)
    assert free_to_gin(book, ("M-3", "M-2", "M-1")) == ("M-3", "M-1")


def test_the_blocked_list_says_what_each_one_is_held_for(book: Book) -> None:
    for tag in ("M-1", "M-2", "M-3"):
        receive(book, a_module(tag))
    place(book, "M-1", HoldReason.PLASTIC, PLACED)
    place(book, "M-3", HoldReason.IDENTITY, PLACED)
    assert blocked(book, ("M-1", "M-2", "M-3")) == {
        "M-1": HoldReason.PLASTIC,
        "M-3": HoldReason.IDENTITY,
    }


def test_nothing_held_gives_an_empty_blocked_list(book: Book) -> None:
    receive(book, a_module("M-1"))
    assert blocked(book, ("M-1",)) == {}
    assert free_to_gin(book, ()) == ()
