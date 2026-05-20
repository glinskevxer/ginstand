"""The instrument register and the calibration log."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.model.instrument import Calibration, Instrument, InstrumentKind
from ginstand.store.instruments import CalibrationStore, InstrumentStore

CHECKED = date(2025, 8, 1)


@pytest.fixture
def kit(book: sqlite3.Connection) -> sqlite3.Connection:
    store = InstrumentStore(book)
    store.add(Instrument(ref="SC-1", kind=InstrumentKind.TRUCK_SCALE, description="Weighbridge"))
    store.add(Instrument(ref="MM-1", kind=InstrumentKind.MOISTURE_METER, description="Yard meter"))
    return book


def test_an_instrument_reads_back_whole(kit: sqlite3.Connection) -> None:
    found = InstrumentStore(kit).get("sc-1")
    assert found.kind is InstrumentKind.TRUCK_SCALE
    assert found.description == "Weighbridge"
    assert found.in_service


def test_adding_the_same_reference_twice_is_refused(kit: sqlite3.Connection) -> None:
    with pytest.raises(DuplicateError, match="instrument SC-1"):
        InstrumentStore(kit).add(
            Instrument(ref="SC-1", kind=InstrumentKind.BALE_SCALE, description="Other")
        )


def test_retiring_writes_through(kit: sqlite3.Connection) -> None:
    store = InstrumentStore(kit)
    store.save(
        Instrument(
            ref="SC-1",
            kind=InstrumentKind.TRUCK_SCALE,
            description="Weighbridge",
            retired=date(2026, 1, 1),
        )
    )
    assert not store.get("SC-1").in_service
    assert [item.ref for item in store.in_service()] == ["MM-1"]


def test_saving_something_that_is_not_there_is_refused(
    kit: sqlite3.Connection,
) -> None:
    with pytest.raises(NotFoundError, match="no instrument with reference SC-9"):
        InstrumentStore(kit).save(
            Instrument(ref="SC-9", kind=InstrumentKind.BALE_SCALE, description="Nowhere")
        )


def test_instruments_list_by_kind(kit: sqlite3.Connection) -> None:
    store = InstrumentStore(kit)
    assert [i.ref for i in store.of_kind(InstrumentKind.MOISTURE_METER)] == ["MM-1"]
    assert store.of_kind(InstrumentKind.COLORIMETER) == ()


def test_a_check_reads_back_with_an_id(kit: sqlite3.Connection) -> None:
    store = CalibrationStore(kit)
    logged = store.record(
        Calibration(instrument="SC-1", checked=CHECKED, error=Decimal("12"), passed=True)
    )
    assert logged.calibration_id > 0
    assert store.get(logged.calibration_id) == logged


def test_a_check_against_an_instrument_that_is_not_there_is_refused(
    kit: sqlite3.Connection,
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        CalibrationStore(kit).record(
            Calibration(instrument="SC-9", checked=CHECKED, error=Decimal("0"), passed=True)
        )


def test_the_history_reads_oldest_first(kit: sqlite3.Connection) -> None:
    store = CalibrationStore(kit)
    store.record(
        Calibration(instrument="SC-1", checked=date(2026, 2, 1), error=Decimal("8"), passed=True)
    )
    store.record(Calibration(instrument="SC-1", checked=CHECKED, error=Decimal("12"), passed=True))
    assert [c.checked for c in store.history_for("sc-1")] == [
        CHECKED,
        date(2026, 2, 1),
    ]


def test_the_last_check_before_a_day_is_found(kit: sqlite3.Connection) -> None:
    store = CalibrationStore(kit)
    store.record(Calibration(instrument="SC-1", checked=CHECKED, error=Decimal("12"), passed=True))
    store.record(
        Calibration(instrument="SC-1", checked=date(2026, 2, 1), error=Decimal("8"), passed=True)
    )
    found = store.last_before("SC-1", date(2025, 10, 14))
    assert found is not None
    assert found.checked == CHECKED
    assert store.last_before("SC-1", date(2025, 7, 1)) is None


def test_the_failures_can_be_listed(kit: sqlite3.Connection) -> None:
    store = CalibrationStore(kit)
    store.record(Calibration(instrument="SC-1", checked=CHECKED, error=Decimal("12"), passed=True))
    store.record(
        Calibration(instrument="MM-1", checked=CHECKED, error=Decimal("2.4"), passed=False)
    )
    assert [c.instrument for c in store.failures()] == ["MM-1"]
    assert store.count() == 2


def test_a_check_that_is_not_there_reads_as_missing(kit: sqlite3.Connection) -> None:
    store = CalibrationStore(kit)
    assert store.find(41) is None
    with pytest.raises(NotFoundError, match="no calibration with reference 41"):
        store.get(41)
