"""The order the cotton wants and the order the yard can feed are not the same."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import NotFoundError, StateError
from ginstand.ginning.run import feed, open_run
from ginstand.store.book import Book
from ginstand.yard.order import queue
from ginstand.yard.places import (
    buried,
    digging,
    lift,
    next_position,
    place_of,
    put,
    row_listing,
    row_order,
    rows,
)
from ginstand.yard.receiving import receive

from .conftest import a_module

PLACED = date(2025, 10, 2)
TODAY = date(2025, 10, 12)


def stood(book: Book, tag: str, row: str, **changes: object) -> None:
    receive(book, a_module(tag, **changes))
    put(book, tag, row, PLACED)


def test_nothing_is_placed_to_start_with(book: Book) -> None:
    receive(book, a_module("M-1"))
    assert place_of(book, "M-1") is None
    assert rows(book) == ()


def test_a_module_stands_at_the_open_end_of_a_row(book: Book) -> None:
    receive(book, a_module("M-1"))
    assert next_position(book, "A") == 1
    placed = put(book, "M-1", "a", PLACED)
    assert placed.row == "A"
    assert placed.position == 1
    assert next_position(book, "A") == 2


def test_a_row_fills_from_one_end(book: Book) -> None:
    for tag in ("M-1", "M-2", "M-3"):
        stood(book, tag, "A")
    assert [item.module for item in row_listing(book, "A")] == ["M-1", "M-2", "M-3"]
    assert [item.position for item in row_listing(book, "A")] == [1, 2, 3]


def test_a_module_stands_in_one_place_only(book: Book) -> None:
    stood(book, "M-1", "A")
    with pytest.raises(StateError, match="is already standing in the yard"):
        put(book, "M-1", "B", PLACED)


def test_a_ginned_module_cannot_be_stood_in_the_yard(book: Book) -> None:
    receive(book, a_module("M-1"))
    open_run(book, "GR-1", "41207", date(2025, 10, 14))
    feed(book, "GR-1", "M-1", date(2025, 10, 14))
    with pytest.raises(StateError, match="has already been ginned"):
        put(book, "M-1", "A", date(2025, 10, 14))


def test_a_module_cannot_stand_before_it_arrived(book: Book) -> None:
    receive(book, a_module("M-1", received=date(2025, 10, 2)))
    with pytest.raises(StateError, match="before module M-1 was received"):
        put(book, "M-1", "A", date(2025, 10, 1))


def test_lifting_frees_the_place(book: Book) -> None:
    stood(book, "M-1", "A")
    gone = lift(book, "M-1")
    assert gone.position == 1
    assert place_of(book, "M-1") is None
    assert row_listing(book, "A") == ()


def test_lifting_something_that_is_not_placed_is_refused(book: Book) -> None:
    receive(book, a_module("M-1"))
    with pytest.raises(NotFoundError, match="no yard place with reference M-1"):
        lift(book, "M-1")


def test_the_rows_with_something_in_them_are_listed(book: Book) -> None:
    stood(book, "M-1", "B")
    stood(book, "M-2", "A")
    assert rows(book) == ("A", "B")


def test_the_modules_in_front_of_one_are_named(book: Book) -> None:
    for tag in ("M-1", "M-2", "M-3"):
        stood(book, tag, "A")
    assert buried(book, "M-1") == ("M-2", "M-3")
    assert buried(book, "M-3") == ()


def test_asking_about_an_unplaced_module_is_refused(book: Book) -> None:
    receive(book, a_module("M-1"))
    with pytest.raises(NotFoundError, match="no yard place with reference M-1"):
        buried(book, "M-1")


def test_a_module_at_the_back_waits_for_the_ones_in_front(book: Book) -> None:
    stood(book, "M-1", "A", moisture_pct=Decimal("13.0"), received=date(2025, 10, 2))
    stood(book, "M-2", "A", moisture_pct=Decimal("7.0"), received=date(2025, 10, 2))
    tags = ("M-1", "M-2")
    assert queue(book, tags, TODAY)[0] == "M-1"
    assert row_order(book, tags, TODAY) == ("M-2", "M-1")


def test_the_two_orders_agree_when_the_worst_is_at_the_open_end(book: Book) -> None:
    stood(book, "M-1", "A", moisture_pct=Decimal("7.0"))
    stood(book, "M-2", "A", moisture_pct=Decimal("13.0"))
    tags = ("M-1", "M-2")
    assert queue(book, tags, TODAY) == row_order(book, tags, TODAY)
    assert digging(book, tags, TODAY) == 0


def test_the_digging_counts_how_far_out_the_orders_are(book: Book) -> None:
    stood(book, "M-1", "A", moisture_pct=Decimal("13.0"))
    stood(book, "M-2", "A", moisture_pct=Decimal("7.0"))
    assert digging(book, ("M-1", "M-2"), TODAY) == 2


def test_an_unmapped_module_is_treated_as_reachable(book: Book) -> None:
    receive(book, a_module("M-1", moisture_pct=Decimal("13.0")))
    stood(book, "M-2", "A", moisture_pct=Decimal("7.0"))
    assert row_order(book, ("M-1", "M-2"), TODAY)[0] == "M-1"


def test_an_empty_queue_orders_to_nothing(book: Book) -> None:
    assert row_order(book, (), TODAY) == ()


def test_the_place_line_reads_as_a_yard_map_row(book: Book) -> None:
    stood(book, "M-1", "A")
    placed = place_of(book, "M-1")
    assert placed is not None
    assert placed.line == "A-01  M-1"
