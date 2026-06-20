"""Logging a stop, and what the stops do to a run's bales an hour.

Bales an hour is the number a gin manager is judged on, and it is meaningless
without the downtime log. A run that made four hundred bales over three days did
it in a certain number of hours, and the hours it did not run are not hours it
was slow, they are hours it was stopped.

So the run's running time is its days multiplied by the shift, less the minutes
in the log. That is where the composition sits: the downtime decides the
denominator, so writing a stop down makes the gin look faster and not slower,
which is the incentive the log needs to have if anybody is going to keep it.

A run with no stops logged is not assumed to have run flat out. It is reported
as having no downtime recorded, which is a different thing and reads differently
on the sheet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from ginstand.errors import StateError
from ginstand.model.downtime import Stop, StopReason
from ginstand.store.book import Book

SHIFT_MINUTES = 720
"""A twelve hour shift. The day a run's hours are counted against."""


@dataclass(frozen=True, slots=True)
class Efficiency:
    """How a run went, once the stops are taken off."""

    run: str
    days: int
    shift_minutes: int
    stopped_minutes: int
    stops: int
    bales: int
    worst_reason: StopReason | None
    worst_minutes: int

    @property
    def scheduled_minutes(self) -> int:
        """The minutes the gin was meant to be running."""
        return self.days * self.shift_minutes

    @property
    def running_minutes(self) -> int:
        """The minutes it actually ran."""
        return max(self.scheduled_minutes - self.stopped_minutes, 0)

    @property
    def running_hours(self) -> Decimal:
        """The hours it actually ran, to two places."""
        return (Decimal(self.running_minutes) / 60).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def uptime(self) -> Decimal:
        """The share of the scheduled minutes it ran, to two places."""
        if self.scheduled_minutes == 0:
            return Decimal("0.00")
        return (Decimal(self.running_minutes) * 100 / self.scheduled_minutes).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def bales_an_hour(self) -> Decimal:
        """Bales an hour over the time it was actually running."""
        if self.running_minutes == 0:
            raise StateError(f"gin run {self.run} ran for no time at all")
        return (Decimal(self.bales) * 60 / self.running_minutes).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def logged(self) -> bool:
        """Whether anybody wrote a stop down for this run."""
        return self.stops > 0

    @property
    def line(self) -> str:
        """The line the run sheet prints."""
        if not self.logged:
            return (
                f"{self.run}  {self.bales} bales over {self.running_hours} h  no downtime recorded"
            )
        worst = f", worst {self.worst_reason} {self.worst_minutes} min"
        return (
            f"{self.run}  {self.bales} bales over {self.running_hours} h  "
            f"{self.bales_an_hour} an hour  {self.uptime}% up{worst}"
        )


def log_stop(
    book: Book,
    run_ref: str,
    on: date,
    started: int,
    minutes: int,
    reason: StopReason,
    note: str = "",
) -> Stop:
    """Write a stop down against a run."""
    run = book.runs.get(run_ref)
    if not run.covers(on):
        raise StateError(
            f"{on.isoformat()} is outside gin run {run.ref}, which opened "
            f"on {run.opened.isoformat()}"
        )
    wanted = Stop(
        run=run.ref, stopped=on, started=started, minutes=minutes, reason=reason, note=note
    )
    for standing in book.downtime.for_run(run.ref):
        if standing.overlaps(wanted):
            raise StateError(
                f"gin run {run.ref} is already logged as stopped over "
                f"{standing.line.split('  ')[1]} on {on.isoformat()}"
            )
    return book.downtime.log(wanted)


def efficiency(book: Book, run_ref: str, shift_minutes: int = SHIFT_MINUTES) -> Efficiency:
    """How a run went, once the stops are taken off."""
    run = book.runs.get(run_ref)
    if run.is_open:
        raise StateError(f"gin run {run.ref} is still open, so its hours are not final")
    stops = book.downtime.for_run(run.ref)
    split = book.downtime.minutes_by_reason(run.ref)
    worst = next(iter(split), None)
    return Efficiency(
        run=run.ref,
        days=run.hours_span_days,
        shift_minutes=shift_minutes,
        stopped_minutes=book.downtime.minutes_for(run.ref),
        stops=len(stops),
        bales=book.bales.count_for_run(run.ref),
        worst_reason=worst,
        worst_minutes=split.get(worst, 0) if worst is not None else 0,
    )


def season_minutes(book: Book, crop_year: int) -> dict[StopReason, int]:
    """Every minute the gin was stopped in a crop year, split by reason."""
    found: dict[StopReason, int] = {}
    for run in book.runs.for_crop_year(crop_year):
        for reason, minutes in book.downtime.minutes_by_reason(run.ref).items():
            found[reason] = found.get(reason, 0) + minutes
    return dict(sorted(found.items(), key=lambda item: -item[1]))
