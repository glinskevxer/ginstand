"""The downtime decides the denominator, so writing a stop down helps the figure."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import StateError
from ginstand.ginning.downtime import SHIFT_MINUTES, efficiency, log_stop, season_minutes
from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.model.downtime import StopReason
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

from .conftest import GIN, a_module

OPENED = date(2025, 10, 14)


def a_run(book: Book, ref: str = "GR-1", bales: int = 60, days: int = 1) -> None:
    open_run(book, ref, GIN, OPENED)
    tag = f"M-{ref}"
    receive(book, a_module(tag, gross_pounds=76_140, tare_pounds=26_140))
    feed(book, ref, tag, OPENED)
    for _ in range(bales):
        press(book, ref, OPENED, 512, 22, Decimal("6.8"))
    close_run(book, ref, date(2025, 10, 13 + days))


def test_a_stop_is_written_against_the_run(book: Book) -> None:
    a_run(book)
    stop = log_stop(book, "GR-1", OPENED, 570, 45, StopReason.CHOKE, "feeder")
    assert stop.run == "GR-1"
    assert stop.minutes == 45
    assert book.downtime.minutes_for("GR-1") == 45


def test_a_stop_outside_the_run_is_refused(book: Book) -> None:
    a_run(book)
    with pytest.raises(StateError, match="outside gin run GR-1"):
        log_stop(book, "GR-1", date(2025, 10, 13), 570, 45, StopReason.CHOKE)


def test_two_stops_that_share_a_minute_are_refused(book: Book) -> None:
    a_run(book)
    log_stop(book, "GR-1", OPENED, 570, 45, StopReason.CHOKE)
    with pytest.raises(StateError, match="already logged as stopped"):
        log_stop(book, "GR-1", OPENED, 600, 30, StopReason.BREAKDOWN)


def test_two_stops_that_do_not_touch_are_both_taken(book: Book) -> None:
    a_run(book)
    log_stop(book, "GR-1", OPENED, 570, 45, StopReason.CHOKE)
    log_stop(book, "GR-1", OPENED, 615, 30, StopReason.BREAKDOWN)
    assert book.downtime.minutes_for("GR-1") == 75


def test_an_open_run_has_no_final_hours(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    with pytest.raises(StateError, match="still open, so its hours are not final"):
        efficiency(book, "GR-1")


def test_a_run_with_no_stops_says_none_were_recorded(book: Book) -> None:
    a_run(book)
    figure = efficiency(book, "GR-1")
    assert not figure.logged
    assert figure.stopped_minutes == 0
    assert figure.running_minutes == SHIFT_MINUTES
    assert "no downtime recorded" in figure.line


def test_the_stops_come_off_the_running_time(book: Book) -> None:
    a_run(book)
    log_stop(book, "GR-1", OPENED, 570, 120, StopReason.BREAKDOWN)
    figure = efficiency(book, "GR-1")
    assert figure.scheduled_minutes == SHIFT_MINUTES
    assert figure.running_minutes == SHIFT_MINUTES - 120
    assert figure.running_hours == Decimal("10.00")


def test_writing_a_stop_down_makes_the_gin_look_faster(book: Book) -> None:
    a_run(book)
    before = efficiency(book, "GR-1").bales_an_hour
    log_stop(book, "GR-1", OPENED, 570, 120, StopReason.BREAKDOWN)
    after = efficiency(book, "GR-1").bales_an_hour
    assert after > before


def test_the_uptime_is_the_share_that_ran(book: Book) -> None:
    a_run(book)
    log_stop(book, "GR-1", OPENED, 570, 72, StopReason.CHOKE)
    assert efficiency(book, "GR-1").uptime == Decimal("90.00")


def test_the_worst_reason_is_named(book: Book) -> None:
    a_run(book)
    log_stop(book, "GR-1", OPENED, 570, 30, StopReason.CHOKE)
    log_stop(book, "GR-1", OPENED, 700, 120, StopReason.WAITING)
    figure = efficiency(book, "GR-1")
    assert figure.worst_reason is StopReason.WAITING
    assert figure.worst_minutes == 120
    assert "worst waiting on modules" in figure.line


def test_a_longer_run_has_more_scheduled_time(book: Book) -> None:
    a_run(book, days=3)
    assert efficiency(book, "GR-1").scheduled_minutes == 3 * SHIFT_MINUTES


def test_the_shift_length_can_be_given(book: Book) -> None:
    a_run(book)
    assert efficiency(book, "GR-1", 480).scheduled_minutes == 480


def test_a_run_stopped_all_shift_has_no_bales_an_hour(book: Book) -> None:
    a_run(book)
    log_stop(book, "GR-1", OPENED, 0, SHIFT_MINUTES, StopReason.BREAKDOWN)
    figure = efficiency(book, "GR-1")
    assert figure.running_minutes == 0
    with pytest.raises(StateError, match="ran for no time at all"):
        assert figure.bales_an_hour


def test_the_season_adds_the_reasons_across_runs(book: Book) -> None:
    a_run(book, "GR-1")
    log_stop(book, "GR-1", OPENED, 570, 30, StopReason.CHOKE)
    a_run(book, "GR-2", bales=10)
    log_stop(book, "GR-2", OPENED, 700, 90, StopReason.CHOKE)
    log_stop(book, "GR-2", OPENED, 800, 45, StopReason.POWER)
    split = season_minutes(book, 2025)
    assert list(split) == [StopReason.CHOKE, StopReason.POWER]
    assert split[StopReason.CHOKE] == 120


def test_a_crop_year_with_no_stops_has_nothing(book: Book) -> None:
    a_run(book)
    assert season_minutes(book, 2025) == {}
