"""The interval belongs to the kind, and a failed check vouches for nothing."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import ValidationError
from ginstand.model.instrument import (
    INTERVALS,
    TOLERANCES,
    Calibration,
    Instrument,
    InstrumentKind,
)

CHECKED = date(2025, 8, 1)


def an_instrument(**changes: object) -> Instrument:
    fields: dict[str, object] = {
        "ref": "sc-1",
        "kind": InstrumentKind.TRUCK_SCALE,
        "description": "  Weighbridge  ",
        "serial": " tb-4471 ",
    }
    fields.update(changes)
    return Instrument(**fields)  # type: ignore[arg-type]


def a_check(**changes: object) -> Calibration:
    fields: dict[str, object] = {
        "instrument": "sc-1",
        "checked": CHECKED,
        "error": Decimal("12"),
        "passed": True,
        "by_whom": "State Weights",
    }
    fields.update(changes)
    return Calibration(**fields)  # type: ignore[arg-type]


def test_an_instrument_normalises_its_reference_and_serial() -> None:
    instrument = an_instrument()
    assert instrument.ref == "SC-1"
    assert instrument.description == "Weighbridge"
    assert instrument.serial == "TB-4471"


def test_an_instrument_without_a_description_is_refused() -> None:
    with pytest.raises(ValidationError, match="description: is empty"):
        an_instrument(description="  ")


def test_the_interval_belongs_to_the_kind_not_the_machine() -> None:
    assert an_instrument().interval == INTERVALS[InstrumentKind.TRUCK_SCALE]
    meter = an_instrument(kind=InstrumentKind.MOISTURE_METER)
    assert meter.interval == 30
    assert meter.interval < an_instrument().interval


def test_every_kind_has_an_interval_and_a_tolerance() -> None:
    for kind in InstrumentKind:
        assert kind in INTERVALS
        assert kind in TOLERANCES


def test_a_meter_is_checked_more_often_than_a_scale() -> None:
    assert INTERVALS[InstrumentKind.MOISTURE_METER] < INTERVALS[InstrumentKind.TRUCK_SCALE]


def test_an_instrument_is_in_service_until_it_is_retired() -> None:
    assert an_instrument().in_service
    retired = an_instrument(retired=date(2026, 1, 1))
    assert not retired.in_service
    assert retired.working_on(date(2025, 12, 31))
    assert not retired.working_on(date(2026, 1, 1))


def test_a_check_quantises_its_error() -> None:
    assert a_check(error=Decimal("12.3456")).error == Decimal("12.346")


def test_the_next_check_is_due_an_interval_later() -> None:
    assert a_check().due(182) == date(2026, 1, 30)


def test_a_passed_check_vouches_for_the_days_it_covers() -> None:
    check = a_check()
    assert check.covers(CHECKED, 182)
    assert check.covers(date(2025, 10, 14), 182)
    assert check.covers(check.due(182), 182)
    assert not check.covers(date(2026, 2, 1), 182)


def test_a_check_vouches_for_nothing_before_it() -> None:
    assert not a_check().covers(date(2025, 7, 31), 182)


def test_a_failed_check_vouches_for_nothing_at_all() -> None:
    failed = a_check(passed=False)
    assert not failed.covers(CHECKED, 182)
    assert not failed.covers(date(2025, 10, 14), 182)


def test_a_failed_check_prints_loudly() -> None:
    assert "FAIL" in a_check(passed=False).line
    assert "pass" in a_check().line


def test_a_check_is_frozen() -> None:
    check = a_check()
    with pytest.raises(AttributeError):
        check.passed = False  # type: ignore[misc]
