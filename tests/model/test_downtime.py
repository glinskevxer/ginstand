"""A stop is a day and two numbers, which is what the paper log has on it."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import ValidationError
from ginstand.model.downtime import (
    MINUTES_IN_A_DAY,
    Stop,
    StopReason,
    clock,
    format_clock,
    parse_clock,
)

STOPPED = date(2025, 10, 14)


def a_stop(**changes: object) -> Stop:
    fields: dict[str, object] = {
        "run": "gr-1",
        "stopped": STOPPED,
        "started": 9 * 60 + 30,
        "minutes": 45,
        "reason": StopReason.CHOKE,
    }
    fields.update(changes)
    return Stop(**fields)  # type: ignore[arg-type]


def test_a_time_of_day_is_minutes_past_midnight() -> None:
    assert clock(0) == 0
    assert clock(MINUTES_IN_A_DAY - 1) == MINUTES_IN_A_DAY - 1


@pytest.mark.parametrize("minutes", [-1, MINUTES_IN_A_DAY, MINUTES_IN_A_DAY + 60])
def test_a_time_outside_the_day_is_refused(minutes: int) -> None:
    with pytest.raises(ValidationError, match="must be between 0 and 1439"):
        clock(minutes)


def test_a_bool_is_not_a_time() -> None:
    with pytest.raises(ValidationError, match="whole number of minutes"):
        clock(True)


@pytest.mark.parametrize(
    ("written", "minutes"),
    [("09:30", 570), ("9:30", 570), ("00:00", 0), ("23:59", 1439), ("9.30", 570)],
)
def test_a_time_reads_off_the_paper_log(written: str, minutes: int) -> None:
    assert parse_clock(written) == minutes


@pytest.mark.parametrize("written", ["", "930", "9:60", "nine", "9:aa", "25:00"])
def test_a_time_that_is_not_hh_mm_is_refused(written: str) -> None:
    with pytest.raises(ValidationError):
        parse_clock(written)


def test_a_time_prints_back_the_way_it_was_written() -> None:
    assert format_clock(570) == "09:30"
    assert format_clock(0) == "00:00"
    assert format_clock(1439) == "23:59"


def test_a_stop_carries_its_end_and_its_hours() -> None:
    stop = a_stop()
    assert stop.ended == 10 * 60 + 15
    assert stop.hours == Decimal("0.75")
    assert stop.run == "GR-1"


def test_a_stop_of_nothing_is_not_a_stop() -> None:
    with pytest.raises(ValidationError, match="is not a stop"):
        a_stop(minutes=0)


def test_a_stop_that_runs_past_midnight_is_two_stops() -> None:
    with pytest.raises(ValidationError, match="runs past midnight, so it is two stops"):
        a_stop(started=23 * 60, minutes=120)


def test_a_stop_ending_exactly_at_midnight_is_one_stop() -> None:
    assert a_stop(started=23 * 60, minutes=60).ended == MINUTES_IN_A_DAY


def test_two_stops_that_share_a_minute_overlap() -> None:
    first = a_stop(started=570, minutes=45)
    assert first.overlaps(a_stop(started=600, minutes=30))
    assert not first.overlaps(a_stop(started=615, minutes=30))
    assert not first.overlaps(a_stop(started=500, minutes=70))


def test_stops_on_different_days_or_runs_never_overlap() -> None:
    first = a_stop()
    assert not first.overlaps(a_stop(stopped=date(2025, 10, 15)))
    assert not first.overlaps(a_stop(run="GR-2"))


def test_waiting_is_its_own_reason() -> None:
    assert str(StopReason.WAITING) == "waiting on modules"
    assert StopReason("choke") is StopReason.CHOKE
    assert len(set(StopReason)) == 7


def test_the_log_line_reads_as_the_paper_one() -> None:
    assert a_stop().line == "2025-10-14  09:30-10:15    45 min  choke"
