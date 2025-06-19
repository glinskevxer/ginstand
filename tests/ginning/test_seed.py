"""Seed goes out by the truck, so the total is not final when the run closes."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import StateError, ValidationError
from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.ginning.seed import (
    SEED_GRACE_DAYS,
    loads_for,
    record_load,
    seed_by_producer,
    seed_pounds,
    seed_turnout,
    turnout_in_band,
    waste_pounds,
)
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

from .conftest import GIN, a_module

OPENED = date(2025, 10, 14)


def run_with(book: Book, seed_cotton: int = 100_000, bales: int = 0) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    receive(
        book,
        a_module("M-1", gross_pounds=26_140 + min(seed_cotton, 33_800), tare_pounds=26_140),
    )
    feed(book, "GR-1", "M-1", OPENED)
    remaining = seed_cotton - min(seed_cotton, 33_800)
    tag = 2
    while remaining > 0:
        piece = min(remaining, 33_800)
        receive(book, a_module(f"M-{tag}", gross_pounds=26_140 + piece, tare_pounds=26_140))
        feed(book, "GR-1", f"M-{tag}", OPENED)
        remaining -= piece
        tag += 1
    for _ in range(bales):
        press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))


def test_a_seed_load_is_booked_against_the_run(book: Book) -> None:
    run_with(book)
    load = record_load(book, "GR-1", OPENED, 20_400, ticket="S-1", buyer="Delta Oil")
    assert load.load_id > 0
    assert load.net_pounds == 20_400
    assert load.buyer == "Delta Oil"
    assert seed_pounds(book, "GR-1") == 20_400


def test_several_loads_add_up(book: Book) -> None:
    run_with(book)
    record_load(book, "GR-1", OPENED, 20_400)
    record_load(book, "GR-1", date(2025, 10, 15), 18_900)
    assert seed_pounds(book, "GR-1") == 39_300
    assert [load.net_pounds for load in loads_for(book, "GR-1")] == [20_400, 18_900]


def test_a_run_with_no_seed_yet_has_none(book: Book) -> None:
    run_with(book)
    assert seed_pounds(book, "GR-1") == 0
    assert loads_for(book, "GR-1") == ()


def test_a_load_before_the_run_opened_is_refused(book: Book) -> None:
    run_with(book)
    with pytest.raises(StateError, match="before gin run GR-1 opened"):
        record_load(book, "GR-1", date(2025, 10, 13), 20_400)


def test_a_load_inside_the_grace_after_closing_is_taken(book: Book) -> None:
    run_with(book, bales=1)
    close_run(book, "GR-1", OPENED)
    late = OPENED.replace(day=OPENED.day + SEED_GRACE_DAYS)
    assert record_load(book, "GR-1", late, 5_000).net_pounds == 5_000


def test_a_load_past_the_grace_is_refused(book: Book) -> None:
    run_with(book, bales=1)
    close_run(book, "GR-1", OPENED)
    too_late = OPENED.replace(day=OPENED.day + SEED_GRACE_DAYS + 1)
    with pytest.raises(StateError, match=f"past the {SEED_GRACE_DAYS} day grace"):
        record_load(book, "GR-1", too_late, 5_000)


def test_a_load_with_no_weight_is_refused(book: Book) -> None:
    run_with(book)
    with pytest.raises(ValidationError, match="at least 1 lb"):
        record_load(book, "GR-1", OPENED, 0)


def test_a_repeated_seed_ticket_is_refused(book: Book) -> None:
    run_with(book)
    record_load(book, "GR-1", OPENED, 20_400, ticket="S-1")
    with pytest.raises(sqlite3.IntegrityError):
        record_load(book, "GR-1", OPENED, 18_900, ticket="S-1")


def test_loads_with_no_ticket_do_not_collide(book: Book) -> None:
    run_with(book)
    record_load(book, "GR-1", OPENED, 20_400)
    record_load(book, "GR-1", OPENED, 18_900)
    assert len(loads_for(book, "GR-1")) == 2


def test_seed_turnout_is_seed_over_seed_cotton(book: Book) -> None:
    run_with(book, seed_cotton=100_000)
    record_load(book, "GR-1", OPENED, 49_000)
    assert seed_turnout(book, "GR-1") == Decimal("0.4900")
    assert turnout_in_band(book, "GR-1")


def test_a_seed_turnout_outside_the_band_is_flagged(book: Book) -> None:
    run_with(book, seed_cotton=100_000)
    record_load(book, "GR-1", OPENED, 30_000)
    assert not turnout_in_band(book, "GR-1")


def test_waste_is_what_went_in_less_what_came_out(book: Book) -> None:
    run_with(book, seed_cotton=100_000, bales=60)
    record_load(book, "GR-1", OPENED, 49_000)
    assert waste_pounds(book, "GR-1") == 100_000 - 49_000 - 60 * 490


def test_producing_more_than_went_in_is_refused_rather_than_printed(book: Book) -> None:
    run_with(book, seed_cotton=100_000, bales=60)
    record_load(book, "GR-1", OPENED, 90_000)
    with pytest.raises(StateError, match="so a weight is wrong"):
        waste_pounds(book, "GR-1")


def test_seed_splits_pro_rata_and_adds_back(book: Book) -> None:
    run_with(book, seed_cotton=100_000)
    record_load(book, "GR-1", OPENED, 49_001)
    shares = seed_by_producer(book, "GR-1", {"P-12": 70_000, "P-40": 30_000})
    assert sum(shares.values()) == 49_001
    assert shares == {"P-12": 34_301, "P-40": 14_700}


def test_splitting_seed_with_nobody_in_the_run_is_refused(book: Book) -> None:
    run_with(book)
    with pytest.raises(ValidationError, match="no producer put cotton"):
        seed_by_producer(book, "GR-1", {})
