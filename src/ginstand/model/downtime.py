"""The gin stopping, and why.

Every gin stops. What separates a well run one from a badly run one is not
whether it stopped but whether anybody wrote down why, because the reasons
repeat and the repeating ones are the ones worth spending money on.

A stop is a day, a time it started, and how long it lasted. There is no
timestamp here on purpose: nothing in this package reads a clock, and a
downtime record typed up at the end of a shift from a paper log is a day and two
numbers, which is exactly what the paper log has on it.

Waiting on modules is deliberately its own reason and not lumped in with the
mechanical ones. A gin that stops for an hour because the stands choked and one
that stops for an hour because the yard could not get to a module have the same
hour on the sheet and completely different answers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from ginstand.errors import ValidationError
from ginstand.ids import reference

MINUTES_IN_A_DAY = 24 * 60


class StopReason(StrEnum):
    """Why the gin stopped."""

    CHOKE = "choke"
    """Something jammed. The commonest reason and the cheapest to fix."""

    BREAKDOWN = "breakdown"
    """Something broke. The expensive one."""

    WAITING = "waiting on modules"
    """The yard could not feed the stands. Not a gin problem at all."""

    CLEANING = "cleaning"
    """Planned. It still costs the same hour."""

    POWER = "power"
    """Somebody else's fault, and it still shows in the bales per hour."""

    CHANGEOVER = "changeover"
    """Moving between producers, which is what identity preservation costs."""

    OTHER = "other"


def clock(minutes: int, field: str = "time") -> int:
    """Return ``minutes`` past midnight if it is a time of day."""
    if isinstance(minutes, bool) or not isinstance(minutes, int):
        raise ValidationError(field, "must be a whole number of minutes past midnight")
    if minutes < 0 or minutes >= MINUTES_IN_A_DAY:
        raise ValidationError(field, f"must be between 0 and {MINUTES_IN_A_DAY - 1}, got {minutes}")
    return minutes


def parse_clock(text: str, field: str = "time") -> int:
    """Read a time of day off a paper log, written as hours and minutes."""
    cleaned = text.strip().replace(".", ":")
    if ":" not in cleaned:
        raise ValidationError(field, f"must be written as hh:mm, got {text!r}")
    hours, _, mins = cleaned.partition(":")
    if not hours.isdigit() or not mins.isdigit():
        raise ValidationError(field, f"must be written as hh:mm, got {text!r}")
    if int(mins) >= 60:
        raise ValidationError(field, f"has {mins} minutes in it")
    return clock(int(hours) * 60 + int(mins), field)


def format_clock(minutes: int) -> str:
    """A time of day as it is written on the log."""
    hours, mins = divmod(clock(minutes), 60)
    return f"{hours:02d}:{mins:02d}"


@dataclass(frozen=True, slots=True)
class Stop:
    """One stop, on one run, on one day."""

    run: str
    stopped: date
    started: int
    minutes: int
    reason: StopReason
    note: str = ""
    stop_id: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "run", reference(self.run, "gin run"))
        clock(self.started, "started")
        if isinstance(self.minutes, bool) or not isinstance(self.minutes, int):
            raise ValidationError("minutes", "must be a whole number of minutes")
        if self.minutes < 1:
            raise ValidationError("minutes", f"a stop of {self.minutes} minutes is not a stop")
        if self.started + self.minutes > MINUTES_IN_A_DAY:
            raise ValidationError(
                "minutes",
                f"a stop at {format_clock(self.started)} for {self.minutes} minutes "
                f"runs past midnight, so it is two stops",
            )
        object.__setattr__(self, "note", self.note.strip())

    @property
    def ended(self) -> int:
        """The minute the gin started again."""
        return self.started + self.minutes

    @property
    def hours(self) -> Decimal:
        """The stop in hours, to two places."""
        return (Decimal(self.minutes) / 60).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def overlaps(self, other: Stop) -> bool:
        """Whether two stops on the same day cover any of the same minute."""
        if self.stopped != other.stopped or self.run != other.run:
            return False
        return self.started < other.ended and other.started < self.ended

    @property
    def line(self) -> str:
        """The line the downtime log prints."""
        return (
            f"{self.stopped.isoformat()}  {format_clock(self.started)}"
            f"-{format_clock(self.ended % MINUTES_IN_A_DAY)}  "
            f"{self.minutes:>4} min  {self.reason}"
        )
