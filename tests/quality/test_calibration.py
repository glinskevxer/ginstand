"""What an instrument's state was on a day, read out of the log."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import StateError
from ginstand.model.farm import Farm, Field
from ginstand.model.instrument import Instrument, InstrumentKind
from ginstand.model.module import Module, ModuleKind, WrapKind
from ginstand.model.producer import Lease, LeaseKind, Producer
from ginstand.quality.calibration import (
    State,
    due_on,
    passes,
    record,
    standing_on,
    trusted,
    unvouched_tickets,
)
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

CHECKED = date(2025, 8, 1)


@pytest.fixture
def kit(book: Book) -> Book:
    book.instruments.add(
        Instrument(ref="SC-1", kind=InstrumentKind.TRUCK_SCALE, description="Weighbridge")
    )
    book.instruments.add(
        Instrument(ref="MM-1", kind=InstrumentKind.MOISTURE_METER, description="Meter")
    )
    return book


def a_yard(kit: Book) -> None:
    kit.producers.add(Producer(ref="P-12", name="Aldys Brothers"))
    kit.leases.add(Lease(ref="L-1", tenant="P-12", kind=LeaseKind.OWNER))
    kit.farms.add(Farm(ref="F-3", producer="P-12", name="Home Place"))
    kit.fields.add(
        Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("78.4"), lease="L-1")
    )


def a_module(kit: Book, tag: str, received: date) -> None:
    receive(
        kit,
        Module(
            tag=tag,
            field="FL-9",
            kind=ModuleKind.RECTANGULAR,
            harvested=date(2025, 9, 28),
            received=received,
            gross_pounds=48_200,
            tare_pounds=26_140,
            moisture_pct=Decimal("9.4"),
            wrap=WrapKind.TARP,
        ),
    )


def test_the_tolerance_belongs_to_the_kind(kit: Book) -> None:
    scale = kit.instruments.get("SC-1")
    meter = kit.instruments.get("MM-1")
    assert passes(scale, Decimal("12"))
    assert not passes(meter, Decimal("12"))
    assert passes(meter, Decimal("0.4"))


def test_the_verdict_is_worked_out_not_typed_in(kit: Book) -> None:
    logged = record(kit, "SC-1", CHECKED, Decimal("12"))
    assert logged.passed
    failed = record(kit, "MM-1", CHECKED, Decimal("2.4"))
    assert not failed.passed


def test_a_retired_instrument_cannot_be_checked(kit: Book) -> None:
    kit.instruments.save(
        Instrument(
            ref="SC-1",
            kind=InstrumentKind.TRUCK_SCALE,
            description="Weighbridge",
            retired=date(2025, 7, 1),
        )
    )
    with pytest.raises(StateError, match="was retired on 2025-07-01"):
        record(kit, "SC-1", CHECKED, Decimal("12"))


def test_an_instrument_never_checked_is_never(kit: Book) -> None:
    standing = standing_on(kit, "SC-1", date(2025, 10, 14))
    assert standing.state is State.NEVER
    assert standing.checked is None
    assert not standing.trusted


def test_a_passed_check_covers_the_days_after_it(kit: Book) -> None:
    record(kit, "SC-1", CHECKED, Decimal("12"))
    assert standing_on(kit, "SC-1", date(2025, 10, 14)).state is State.COVERED
    assert trusted(kit, "SC-1", date(2025, 10, 14))


def test_a_check_covers_nothing_before_it(kit: Book) -> None:
    record(kit, "SC-1", CHECKED, Decimal("12"))
    assert standing_on(kit, "SC-1", date(2025, 7, 1)).state is State.NEVER


def test_a_check_that_has_run_out_is_lapsed(kit: Book) -> None:
    record(kit, "SC-1", CHECKED, Decimal("12"))
    assert standing_on(kit, "SC-1", date(2026, 6, 1)).state is State.LAPSED


def test_a_failed_check_leaves_the_instrument_failed(kit: Book) -> None:
    record(kit, "MM-1", CHECKED, Decimal("2.4"))
    standing = standing_on(kit, "MM-1", date(2025, 8, 10))
    assert standing.state is State.FAILED
    assert not standing.trusted


def test_a_later_pass_puts_it_right(kit: Book) -> None:
    record(kit, "MM-1", CHECKED, Decimal("2.4"))
    record(kit, "MM-1", date(2025, 8, 10), Decimal("0.2"))
    assert standing_on(kit, "MM-1", date(2025, 8, 20)).state is State.COVERED
    assert standing_on(kit, "MM-1", date(2025, 8, 5)).state is State.FAILED


def test_the_ones_due_are_the_ones_not_covered(kit: Book) -> None:
    record(kit, "SC-1", CHECKED, Decimal("12"))
    due = due_on(kit, date(2025, 10, 14))
    assert [item.instrument for item in due] == ["MM-1"]


def test_a_retired_instrument_is_never_due(kit: Book) -> None:
    kit.instruments.save(
        Instrument(
            ref="MM-1",
            kind=InstrumentKind.MOISTURE_METER,
            description="Meter",
            retired=date(2025, 9, 1),
        )
    )
    record(kit, "SC-1", CHECKED, Decimal("12"))
    assert due_on(kit, date(2025, 10, 14)) == ()


def test_every_ticket_is_vouched_when_the_scale_was_covered(kit: Book) -> None:
    a_yard(kit)
    record(kit, "SC-1", CHECKED, Decimal("12"))
    a_module(kit, "M-1", date(2025, 10, 2))
    assert unvouched_tickets(kit, "SC-1") == ()


def test_a_ticket_written_while_the_scale_lapsed_is_listed(kit: Book) -> None:
    a_yard(kit)
    record(kit, "SC-1", CHECKED, Decimal("12"))
    a_module(kit, "M-1", date(2025, 10, 2))
    a_module(kit, "M-2", date(2026, 6, 1))
    assert unvouched_tickets(kit, "SC-1") == ("M-2",)


def test_the_answer_does_not_change_when_the_scale_is_checked_later(
    kit: Book,
) -> None:
    a_yard(kit)
    a_module(kit, "M-1", date(2025, 10, 2))
    assert unvouched_tickets(kit, "SC-1") == ("M-1",)
    record(kit, "SC-1", date(2026, 1, 1), Decimal("8"))
    assert unvouched_tickets(kit, "SC-1") == ("M-1",)


def test_modules_cross_a_truck_scale_and_not_a_meter(kit: Book) -> None:
    a_yard(kit)
    with pytest.raises(StateError, match="is a moisture meter"):
        unvouched_tickets(kit, "MM-1")
