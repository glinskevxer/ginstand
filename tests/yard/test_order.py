"""Worst first, where worst is age multiplied by moisture above the safe line."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import ValidationError
from ginstand.model.hold import HoldReason
from ginstand.store.book import Book
from ginstand.yard.holds import place
from ginstand.yard.order import (
    RISK_LIMIT,
    SAFE_YARD_MOISTURE,
    at_risk,
    entry_for,
    queue,
    spoil_points,
    yard_standing,
)
from ginstand.yard.receiving import receive

from .conftest import a_module

TODAY = date(2025, 10, 12)


def test_a_dry_module_gathers_no_points_however_long_it_sits() -> None:
    module = a_module(
        "M-1",
        harvested=date(2025, 8, 30),
        received=date(2025, 9, 1),
        moisture_pct=SAFE_YARD_MOISTURE,
    )
    assert spoil_points(module, TODAY) == Decimal("0.0")
    assert not at_risk(module, TODAY)


def test_points_are_days_multiplied_by_moisture_over_the_line() -> None:
    module = a_module("M-1", received=date(2025, 10, 2), moisture_pct=Decimal("11.0"))
    assert spoil_points(module, TODAY) == Decimal("30.0")


def test_the_risk_line_is_inclusive() -> None:
    module = a_module("M-1", received=date(2025, 10, 2), moisture_pct=Decimal("11.0"))
    assert spoil_points(module, TODAY) == RISK_LIMIT
    assert at_risk(module, TODAY)


def test_a_wet_module_reaches_the_line_faster_than_an_old_dry_one() -> None:
    wet = a_module("M-1", received=date(2025, 10, 9), moisture_pct=Decimal("18.0"))
    old = a_module(
        "M-2",
        harvested=date(2025, 9, 18),
        received=date(2025, 9, 20),
        moisture_pct=Decimal("8.5"),
    )
    assert at_risk(wet, TODAY)
    assert not at_risk(old, TODAY)


def test_asking_before_the_module_arrived_is_refused() -> None:
    module = a_module("M-1", received=date(2025, 10, 2))
    with pytest.raises(ValidationError, match="before the module was received"):
        spoil_points(module, date(2025, 10, 1))


def test_an_entry_carries_the_numbers_that_put_it_where_it_is(book: Book) -> None:
    receive(book, a_module("M-1", received=date(2025, 10, 2), moisture_pct=Decimal("11.0")))
    entry = entry_for(book, "M-1", TODAY)
    assert entry.producer == "P-12"
    assert entry.days_in_yard == 10
    assert entry.points == Decimal("30.0")
    assert entry.at_risk


def test_the_queue_puts_the_worst_module_first(book: Book) -> None:
    receive(book, a_module("M-1", received=date(2025, 10, 10), moisture_pct=Decimal("8.0")))
    receive(book, a_module("M-2", received=date(2025, 10, 8), moisture_pct=Decimal("12.0")))
    receive(book, a_module("M-3", received=date(2025, 10, 1), moisture_pct=Decimal("8.0")))
    assert queue(book, ("M-1", "M-2", "M-3"), TODAY, group=False) == ("M-2", "M-3", "M-1")


def test_modules_with_no_points_fall_back_to_oldest_first(book: Book) -> None:
    receive(book, a_module("M-1", received=date(2025, 10, 8), moisture_pct=Decimal("7.0")))
    receive(book, a_module("M-2", received=date(2025, 10, 2), moisture_pct=Decimal("7.0")))
    assert queue(book, ("M-1", "M-2"), TODAY, group=False) == ("M-2", "M-1")


def test_a_held_module_is_dropped_rather_than_sorted_to_the_back(book: Book) -> None:
    receive(book, a_module("M-1", received=date(2025, 10, 2), moisture_pct=Decimal("12.0")))
    receive(book, a_module("M-2", received=date(2025, 10, 8), moisture_pct=Decimal("7.0")))
    place(book, "M-1", HoldReason.WET, date(2025, 10, 3))
    assert queue(book, ("M-1", "M-2"), TODAY) == ("M-2",)


def test_grouping_finishes_a_producer_before_moving_on(book: Book) -> None:
    receive(book, a_module("M-1", field="FL-9", received=date(2025, 10, 8)))
    receive(book, a_module("M-2", field="FL-5", received=date(2025, 10, 7)))
    receive(book, a_module("M-3", field="FL-2", received=date(2025, 10, 6)))
    for tag in ("M-1", "M-2", "M-3"):
        assert not entry_for(book, tag, TODAY).at_risk
    assert queue(book, ("M-1", "M-2", "M-3"), TODAY) == ("M-3", "M-1", "M-2")


def test_grouping_off_gives_the_plain_worst_first_order(book: Book) -> None:
    receive(book, a_module("M-1", field="FL-9", received=date(2025, 10, 8)))
    receive(book, a_module("M-2", field="FL-5", received=date(2025, 10, 7)))
    receive(book, a_module("M-3", field="FL-2", received=date(2025, 10, 6)))
    assert queue(book, ("M-1", "M-2", "M-3"), TODAY, group=False) == ("M-3", "M-2", "M-1")


def test_a_module_at_risk_still_jumps_a_grouped_queue(book: Book) -> None:
    receive(
        book, a_module("M-1", field="FL-9", received=date(2025, 10, 9), moisture_pct=Decimal("8.0"))
    )
    receive(
        book, a_module("M-2", field="FL-2", received=date(2025, 10, 9), moisture_pct=Decimal("8.0"))
    )
    receive(
        book,
        a_module("M-9", field="FL-5", received=date(2025, 10, 1), moisture_pct=Decimal("13.0")),
    )
    assert entry_for(book, "M-9", TODAY).at_risk
    assert queue(book, ("M-1", "M-2", "M-9"), TODAY)[0] == "M-9"


def test_an_empty_queue_is_empty(book: Book) -> None:
    assert queue(book, (), TODAY) == ()


def test_the_yard_standing_lists_everything_unginned_including_held(book: Book) -> None:
    receive(book, a_module("M-1", received=date(2025, 10, 2), moisture_pct=Decimal("12.0")))
    receive(book, a_module("M-2", received=date(2025, 10, 8), moisture_pct=Decimal("7.0")))
    place(book, "M-1", HoldReason.WET, date(2025, 10, 3))
    standing = yard_standing(book, TODAY)
    assert [entry.tag for entry in standing] == ["M-1", "M-2"]
    assert standing[0].at_risk
