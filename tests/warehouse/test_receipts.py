"""A bale is receipted only once it is allocated, dry and not already in store."""

from __future__ import annotations

from datetime import date

import pytest

from ginstand.errors import NotFoundError, StateError
from ginstand.store.book import Book
from ginstand.warehouse.receipts import (
    in_store,
    issue,
    next_number,
    receipt_for,
    release,
    transfer,
)

from .conftest import gin_a_run, press_a_run

ISSUED = date(2025, 10, 30)


def test_the_first_receipt_number_comes_out_of_the_book(book: Book) -> None:
    gin_a_run(book)
    assert next_number(book) == "WR-00001"
    assert issue(book, "254120700001", "WH-1", ISSUED).number == "WR-00001"
    assert next_number(book) == "WR-00002"


def test_the_holder_defaults_to_whoever_the_bale_was_allocated_to(book: Book) -> None:
    gin_a_run(book)
    assert issue(book, "254120700001", "WH-1", ISSUED).holder == "P-12"


def test_the_holder_can_be_named_when_the_lot_was_sold_before_it_shipped(
    book: Book,
) -> None:
    gin_a_run(book)
    assert issue(book, "254120700001", "WH-1", ISSUED, holder="p-40").holder == "P-40"


def test_an_unallocated_bale_has_nobody_to_hold_the_receipt(book: Book) -> None:
    press_a_run(book)
    with pytest.raises(StateError, match="has not been allocated"):
        issue(book, "254120700001", "WH-1", ISSUED)


def test_a_bale_already_in_store_names_the_receipt_it_is_under(book: Book) -> None:
    gin_a_run(book)
    issue(book, "254120700001", "WH-1", ISSUED)
    with pytest.raises(StateError, match="already in store under receipt WR-00001"):
        issue(book, "254120700001", "WH-1", ISSUED)


def test_a_receipt_before_the_bale_was_pressed_is_refused(book: Book) -> None:
    gin_a_run(book)
    with pytest.raises(StateError, match="before bale 254120700001 was pressed"):
        issue(book, "254120700001", "WH-1", date(2025, 10, 13))


def test_a_warehouse_that_is_not_in_the_book_is_refused(book: Book) -> None:
    gin_a_run(book)
    with pytest.raises(NotFoundError, match="no warehouse with reference WH-9"):
        issue(book, "254120700001", "WH-9", ISSUED)


def test_releasing_takes_the_bale_out_of_store(book: Book) -> None:
    gin_a_run(book)
    issue(book, "254120700001", "WH-1", ISSUED)
    released = release(book, "WR-00001", date(2026, 2, 10))
    assert not released.outstanding
    assert in_store(book, "P-12") == ()


def test_releasing_twice_is_refused(book: Book) -> None:
    gin_a_run(book)
    issue(book, "254120700001", "WH-1", ISSUED)
    release(book, "WR-00001", date(2026, 2, 10))
    with pytest.raises(StateError, match="was released on 2026-02-10"):
        release(book, "WR-00001", date(2026, 3, 1))


def test_transferring_moves_the_receipt_and_not_the_allocation(book: Book) -> None:
    gin_a_run(book)
    issue(book, "254120700001", "WH-1", ISSUED)
    moved = transfer(book, "WR-00001", "P-40")
    assert moved.holder == "P-40"
    assert book.allocations.owner_of("254120700001") == "P-12"
    assert in_store(book, "P-40") == ("254120700001",)


def test_a_released_receipt_cannot_be_transferred(book: Book) -> None:
    gin_a_run(book)
    issue(book, "254120700001", "WH-1", ISSUED)
    release(book, "WR-00001", date(2026, 2, 10))
    with pytest.raises(StateError, match="has been released"):
        transfer(book, "WR-00001", "P-40")


def test_transferring_to_somebody_who_is_not_in_the_book_is_refused(book: Book) -> None:
    gin_a_run(book)
    issue(book, "254120700001", "WH-1", ISSUED)
    with pytest.raises(NotFoundError, match="no producer with reference P-99"):
        transfer(book, "WR-00001", "P-99")


def test_the_receipt_against_a_bale_can_be_asked_for(book: Book) -> None:
    gin_a_run(book)
    with pytest.raises(NotFoundError, match="no receipt with reference 254120700001"):
        receipt_for(book, "254120700001")
    issue(book, "254120700001", "WH-1", ISSUED)
    assert receipt_for(book, "254120700001").number == "WR-00001"


def test_everything_a_producer_has_in_store_can_be_listed(book: Book) -> None:
    gin_a_run(book)
    assert in_store(book, "P-12") == ()
    for tag in ("254120700001", "254120700002"):
        issue(book, tag, "WH-1", ISSUED)
    assert in_store(book, "P-12") == ("254120700001", "254120700002")
