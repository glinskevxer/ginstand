"""The gin's instruments, and the log of them being checked.

Every number in this package that a producer is paid on came off an instrument:
the truck scale, the bale scale, a moisture meter. A weight off an instrument
that was out of calibration is not a weight, it is a guess, and the only way to
know which one a ticket carries is to be able to ask what the instrument's state
was on the day of the ticket.

So calibration is a log rather than a flag. A flag answers "is it in calibration
now", which is the wrong question in February about a ticket from October.

The interval between checks belongs to the kind of instrument. A truck scale is
checked twice a year because it is legal for trade and a moisture meter is
checked every month because it drifts, and neither of those is a property of the
particular machine.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from ginstand.errors import ValidationError
from ginstand.ids import reference


class InstrumentKind(StrEnum):
    """What sort of instrument it is."""

    TRUCK_SCALE = "truck scale"
    """Legal for trade. Everything a producer is paid on crosses it."""

    BALE_SCALE = "bale scale"
    """Weighs bales at the press."""

    MOISTURE_METER = "moisture meter"
    """Reads seed cotton and lint moisture. Drifts faster than anything else."""

    COLORIMETER = "colorimeter"
    """The gin's own colour reading, which prices nothing but sorts bales."""


INTERVALS: dict[InstrumentKind, int] = {
    InstrumentKind.TRUCK_SCALE: 182,
    InstrumentKind.BALE_SCALE: 182,
    InstrumentKind.MOISTURE_METER: 30,
    InstrumentKind.COLORIMETER: 90,
}
"""Days between checks, by kind. The instrument does not get a say."""

TOLERANCES: dict[InstrumentKind, Decimal] = {
    InstrumentKind.TRUCK_SCALE: Decimal("20"),
    InstrumentKind.BALE_SCALE: Decimal("1"),
    InstrumentKind.MOISTURE_METER: Decimal("0.5"),
    InstrumentKind.COLORIMETER: Decimal("1.0"),
}
"""How far out a check may read and still pass, in the instrument's own units."""


@dataclass(frozen=True, slots=True)
class Instrument:
    """One instrument the gin's numbers come off."""

    ref: str
    kind: InstrumentKind
    description: str
    serial: str = ""
    retired: date | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "ref", reference(self.ref, "instrument"))
        cleaned = self.description.strip()
        if not cleaned:
            raise ValidationError("description", "is empty")
        object.__setattr__(self, "description", cleaned)
        object.__setattr__(self, "serial", self.serial.strip().upper())

    @property
    def interval(self) -> int:
        """Days between checks for this kind of instrument."""
        return INTERVALS[self.kind]

    @property
    def tolerance(self) -> Decimal:
        """How far out a check may read and still pass."""
        return TOLERANCES[self.kind]

    @property
    def in_service(self) -> bool:
        """Whether the instrument is still being used."""
        return self.retired is None

    def working_on(self, day: date) -> bool:
        """Whether the instrument was in service on a day."""
        return self.retired is None or day < self.retired


@dataclass(frozen=True, slots=True)
class Calibration:
    """One check against one instrument."""

    instrument: str
    checked: date
    error: Decimal
    passed: bool
    by_whom: str = ""
    note: str = ""
    calibration_id: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "instrument", reference(self.instrument, "instrument"))
        object.__setattr__(
            self,
            "error",
            Decimal(self.error).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP),
        )
        object.__setattr__(self, "by_whom", self.by_whom.strip())
        object.__setattr__(self, "note", self.note.strip())

    def due(self, interval: int) -> date:
        """The day the next check is due."""
        return self.checked + timedelta(days=interval)

    def covers(self, day: date, interval: int) -> bool:
        """Whether this check vouches for a reading taken on a day.

        A failed check vouches for nothing, including the days before it: an
        instrument found out of tolerance was out of tolerance for some of the
        time since it was last checked, and nobody knows how much.
        """
        return self.passed and self.checked <= day <= self.due(interval)

    @property
    def line(self) -> str:
        """The line the calibration log prints."""
        verdict = "pass" if self.passed else "FAIL"
        return (
            f"{self.checked.isoformat()}  {self.instrument:<10} {verdict:<5} "
            f"error {self.error}  {self.by_whom}"
        )
