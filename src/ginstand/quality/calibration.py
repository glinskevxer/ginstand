"""Recording a check, and asking what an instrument's state was on a day.

The question this module exists to answer is not "is the scale in calibration".
It is "was the scale in calibration on the day this ticket was written", and the
answer is read out of the log rather than off a flag.

Whether a check passes is decided here rather than by whoever ran it. The
tolerance belongs to the kind of instrument, so a moisture meter half a point
out fails and a truck scale twelve pounds out passes, and neither of those is a
judgement the person with the test weights gets to make on the day.

The last function here is what the whole thing is for. Given a day, it lists the
tickets written while the scale that weighed them was not vouched for. Those are
not wrong tickets. They are tickets nobody can say are right, which is a
different and worse thing to find out about in February.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from ginstand.errors import StateError
from ginstand.model.instrument import Calibration, Instrument, InstrumentKind
from ginstand.store.book import Book


class State(StrEnum):
    """What an instrument's calibration was on a day."""

    COVERED = "covered"
    """A passed check covers the day."""

    LAPSED = "lapsed"
    """The last passed check before the day had run out."""

    FAILED = "failed"
    """The last check before the day did not pass."""

    NEVER = "never"
    """There is no check before the day at all."""


@dataclass(frozen=True, slots=True)
class Standing:
    """An instrument's calibration standing on a day."""

    instrument: str
    day: date
    state: State
    checked: date | None
    due: date | None

    @property
    def trusted(self) -> bool:
        """Whether a reading off this instrument on this day is vouched for."""
        return self.state is State.COVERED

    @property
    def line(self) -> str:
        """The line the calibration report prints."""
        when = f" last checked {self.checked.isoformat()}" if self.checked else ""
        until = f", due {self.due.isoformat()}" if self.due else ""
        return f"{self.instrument:<10} {self.state}{when}{until}"


def passes(instrument: Instrument, error: Decimal) -> bool:
    """Whether an error of this size passes for this kind of instrument."""
    return abs(Decimal(error)) <= instrument.tolerance


def record(
    book: Book,
    instrument_ref: str,
    on: date,
    error: Decimal,
    by: str = "",
    note: str = "",
) -> Calibration:
    """Log a check, with the verdict worked out from the kind's tolerance."""
    instrument = book.instruments.get(instrument_ref)
    if not instrument.working_on(on):
        raise StateError(f"instrument {instrument.ref} was retired on {instrument.retired}")
    return book.calibrations.record(
        Calibration(
            instrument=instrument.ref,
            checked=on,
            error=Decimal(error),
            passed=passes(instrument, Decimal(error)),
            by_whom=by,
            note=note,
        )
    )


def standing_on(book: Book, instrument_ref: str, day: date) -> Standing:
    """What an instrument's calibration was on a day."""
    instrument = book.instruments.get(instrument_ref)
    last = book.calibrations.last_before(instrument.ref, day)
    if last is None:
        return Standing(
            instrument=instrument.ref, day=day, state=State.NEVER, checked=None, due=None
        )
    due = last.due(instrument.interval)
    if not last.passed:
        state = State.FAILED
    elif last.covers(day, instrument.interval):
        state = State.COVERED
    else:
        state = State.LAPSED
    return Standing(instrument=instrument.ref, day=day, state=state, checked=last.checked, due=due)


def trusted(book: Book, instrument_ref: str, day: date) -> bool:
    """Whether a reading off an instrument on a day is vouched for."""
    return standing_on(book, instrument_ref, day).trusted


def due_on(book: Book, day: date) -> tuple[Standing, ...]:
    """Every instrument in service that is not covered on a day."""
    return tuple(
        standing
        for instrument in book.instruments.in_service()
        if not (standing := standing_on(book, instrument.ref, day)).trusted
    )


def unvouched_tickets(book: Book, scale_ref: str) -> tuple[str, ...]:
    """Every module weighed in while its scale was not vouched for.

    This is the point of keeping a log rather than a flag. The answer is a list
    of tickets, worked out ticket by ticket against the day each one was
    written, and it does not change when the scale is checked tomorrow.
    """
    scale = book.instruments.get(scale_ref)
    if scale.kind is not InstrumentKind.TRUCK_SCALE:
        raise StateError(
            f"instrument {scale.ref} is a {scale.kind}, and modules cross a truck scale"
        )
    return tuple(
        module.tag
        for module in book.modules.list_all()
        if not trusted(book, scale.ref, module.received)
    )
