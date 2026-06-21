"""Allocation happens once, after closing, and press order follows feed order."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import NotFoundError, StateError
from ginstand.ginning.allocate import (
    allocate,
    bales_of,
    owner_of,
    plan,
    seed_cotton_in_feed_order,
    unallocated_runs,
)
from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

from .conftest import GIN, a_module

OPENED = date(2025, 10, 14)


def run_with(book: Book, ref: str, feeds: tuple[tuple[str, str, int], ...], bales: int) -> None:
    open_run(book, ref, GIN, OPENED)
    for tag, field, net in feeds:
        receive(book, a_module(tag, field=field, gross_pounds=26_140 + net, tare_pounds=26_140))
        feed(book, ref, tag, OPENED)
    for _ in range(bales):
        press(book, ref, OPENED, 512, 22, Decimal("6.8"))
    close_run(book, ref, OPENED)


def test_seed_cotton_is_totalled_in_the_order_producers_fed(book: Book) -> None:
    run_with(
        book,
        "GR-1",
        (("M-1", "FL-5", 10_000), ("M-2", "FL-9", 20_000), ("M-3", "FL-5", 5_000)),
        0,
    )
    assert seed_cotton_in_feed_order(book, "GR-1") == {"P-40": 15_000, "P-12": 20_000}
    assert list(seed_cotton_in_feed_order(book, "GR-1")) == ["P-40", "P-12"]


def test_the_split_follows_the_seed_cotton_weights(book: Book) -> None:
    run_with(book, "GR-1", (("M-1", "FL-9", 30_000), ("M-2", "FL-5", 10_000)), 20)
    split = allocate(book, "GR-1", OPENED)
    assert split.for_producer("P-12").bales == 15
    assert split.for_producer("P-40").bales == 5
    assert sum(share.bales for share in split.shares) == 20


def test_the_first_producer_to_feed_gets_the_first_bales_pressed(book: Book) -> None:
    run_with(book, "GR-1", (("M-1", "FL-9", 30_000), ("M-2", "FL-5", 10_000)), 4)
    allocate(book, "GR-1", OPENED)
    owners = book.allocations.bales_for_run("GR-1")
    assert owners["254120700001"] == "P-12"
    assert owners["254120700003"] == "P-12"
    assert owners["254120700004"] == "P-40"


def test_planning_an_allocation_writes_nothing(book: Book) -> None:
    run_with(book, "GR-1", (("M-1", "FL-9", 30_000), ("M-2", "FL-5", 10_000)), 20)
    assert plan(book, "GR-1").for_producer("P-12").bales == 15
    assert not book.allocations.run_is_allocated("GR-1")


def test_an_open_run_cannot_be_allocated(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    receive(book, a_module("M-1"))
    feed(book, "GR-1", "M-1", OPENED)
    press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
    with pytest.raises(StateError, match="still open, so its bales cannot be allocated"):
        allocate(book, "GR-1", OPENED)


def test_allocating_twice_is_refused(book: Book) -> None:
    run_with(book, "GR-1", (("M-1", "FL-9", 30_000),), 10)
    allocate(book, "GR-1", OPENED)
    with pytest.raises(StateError, match="has already been allocated"):
        allocate(book, "GR-1", OPENED)


def test_a_run_that_pressed_no_bales_has_nothing_to_allocate(book: Book) -> None:
    run_with(book, "GR-1", (("M-1", "FL-9", 30_000),), 0)
    with pytest.raises(StateError, match="pressed no bales"):
        allocate(book, "GR-1", OPENED)


def test_the_carry_from_one_run_moves_a_bale_on_the_next(book: Book) -> None:
    run_with(book, "GR-1", (("M-1", "FL-9", 5_000), ("M-2", "FL-5", 5_000)), 1)
    first = allocate(book, "GR-1", OPENED)
    assert first.for_producer("P-12").bales == 1
    assert book.allocations.carry_for("P-40", 2025) == Decimal("0.500000")

    later = date(2025, 10, 20)
    open_run(book, "GR-2", GIN, later)
    for tag, field in (("M-3", "FL-9"), ("M-4", "FL-5")):
        receive(book, a_module(tag, field=field, gross_pounds=31_140, tare_pounds=26_140))
        feed(book, "GR-2", tag, later)
    press(book, "GR-2", later, 512, 22, Decimal("6.8"))
    close_run(book, "GR-2", later)
    second = allocate(book, "GR-2", later)
    assert second.for_producer("P-40").bales == 1
    assert second.for_producer("P-12").bales == 0


def test_the_owner_of_an_allocated_bale_reads_back(book: Book) -> None:
    run_with(book, "GR-1", (("M-1", "FL-9", 30_000),), 3)
    allocate(book, "GR-1", OPENED)
    assert owner_of(book, "254120700001") == "P-12"
    assert bales_of(book, "P-12") == (
        "254120700001",
        "254120700002",
        "254120700003",
    )


def test_an_unallocated_bale_has_no_owner_to_read(book: Book) -> None:
    run_with(book, "GR-1", (("M-1", "FL-9", 30_000),), 3)
    with pytest.raises(NotFoundError, match="no bale allocation with reference"):
        owner_of(book, "254120700001")


def test_the_runs_still_waiting_on_an_allocation_can_be_listed(book: Book) -> None:
    run_with(book, "GR-1", (("M-1", "FL-9", 30_000),), 3)
    assert unallocated_runs(book, 2025) == ("GR-1",)
    allocate(book, "GR-1", OPENED)
    assert unallocated_runs(book, 2025) == ()


def test_an_open_run_is_not_waiting_on_an_allocation(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    assert unallocated_runs(book, 2025) == ()


def test_a_run_with_nothing_in_it_cannot_be_planned(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    with pytest.raises(StateError, match="nothing in it to allocate"):
        plan(book, "GR-1")
