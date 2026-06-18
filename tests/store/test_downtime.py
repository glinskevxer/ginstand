"""The downtime log, split by run, day and reason."""

from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from ginstand.errors import NotFoundError
from ginstand.model.downtime import Stop, StopReason
from ginstand.model.ginrun import GinRun
from ginstand.store.downtime import DowntimeStore
from ginstand.store.runs import RunStore

STOPPED = date(2025, 10, 14)


@pytest.fixture
def ginned(book: sqlite3.Connection) -> sqlite3.Connection:
    runs = RunStore(book)
    runs.add(GinRun(ref="GR-1", crop_year=2025, gin_code="41207", opened=STOPPED))
    runs.add(GinRun(ref="GR-2", crop_year=2025, gin_code="41207", opened=STOPPED))
    return book


def a_stop(**changes: object) -> Stop:
    fields: dict[str, object] = {
        "run": "GR-1",
        "stopped": STOPPED,
        "started": 570,
        "minutes": 45,
        "reason": StopReason.CHOKE,
    }
    fields.update(changes)
    return Stop(**fields)  # type: ignore[arg-type]


def test_a_stop_reads_back_with_an_id(ginned: sqlite3.Connection) -> None:
    store = DowntimeStore(ginned)
    logged = store.log(a_stop(note="feeder"))
    assert logged.stop_id > 0
    assert store.get(logged.stop_id) == logged


def test_a_stop_on_a_run_that_is_not_there_is_refused(
    ginned: sqlite3.Connection,
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        DowntimeStore(ginned).log(a_stop(run="GR-9"))


def test_the_stops_read_back_in_the_order_they_happened(
    ginned: sqlite3.Connection,
) -> None:
    store = DowntimeStore(ginned)
    store.log(a_stop(started=780))
    store.log(a_stop(started=570))
    store.log(a_stop(stopped=date(2025, 10, 13), started=900))
    assert [s.started for s in store.for_run("gr-1")] == [900, 570, 780]


def test_the_minutes_add_up_for_a_run(ginned: sqlite3.Connection) -> None:
    store = DowntimeStore(ginned)
    assert store.minutes_for("GR-1") == 0
    store.log(a_stop(minutes=45))
    store.log(a_stop(started=780, minutes=30))
    assert store.minutes_for("GR-1") == 75
    assert store.minutes_for("GR-2") == 0


def test_the_minutes_split_by_reason_worst_first(ginned: sqlite3.Connection) -> None:
    store = DowntimeStore(ginned)
    store.log(a_stop(minutes=45, reason=StopReason.CHOKE))
    store.log(a_stop(started=780, minutes=120, reason=StopReason.BREAKDOWN))
    store.log(a_stop(started=1000, minutes=20, reason=StopReason.CHOKE))
    split = store.minutes_by_reason("GR-1")
    assert list(split) == [StopReason.BREAKDOWN, StopReason.CHOKE]
    assert split[StopReason.CHOKE] == 65


def test_a_day_reads_back_across_runs(ginned: sqlite3.Connection) -> None:
    store = DowntimeStore(ginned)
    store.log(a_stop(started=570))
    store.log(a_stop(run="GR-2", started=600))
    store.log(a_stop(stopped=date(2025, 10, 15)))
    assert [s.run for s in store.on_day(STOPPED)] == ["GR-1", "GR-2"]


def test_a_stop_can_be_taken_out_again(ginned: sqlite3.Connection) -> None:
    store = DowntimeStore(ginned)
    logged = store.log(a_stop())
    store.remove(logged.stop_id)
    assert store.count() == 0
    assert store.minutes_for("GR-1") == 0


def test_removing_something_that_is_not_there_is_refused(
    ginned: sqlite3.Connection,
) -> None:
    with pytest.raises(NotFoundError, match="no stop with reference 41"):
        DowntimeStore(ginned).remove(41)


def test_a_stop_that_is_not_there_reads_as_missing(
    ginned: sqlite3.Connection,
) -> None:
    store = DowntimeStore(ginned)
    assert store.find(41) is None
    with pytest.raises(NotFoundError, match="no stop with reference 41"):
        store.get(41)
