"""Gin runs: one continuous session on the stands.

A run is opened, modules are fed into it in order, bales come off the press, and
then it is closed. Closing is what makes the run's numbers final, because the
turnout cannot be worked out until the last module is through and the last bale
is pressed.

The record here is the run's own facts. What went into it and what came off it
are separate records that point at the run, so a run can be read without pulling
sixty modules and a hundred bales in behind it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ginstand.errors import ValidationError
from ginstand.ids import gin_code, reference
from ginstand.season import check_crop_year, crop_year_of, require_in_crop_year


@dataclass(frozen=True, slots=True)
class GinRun:
    """One ginning session, open or closed."""

    ref: str
    crop_year: int
    gin_code: str
    opened: date
    closed: date | None = None
    shift: str = ""
    note: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "ref", reference(self.ref, "gin run"))
        check_crop_year(self.crop_year)
        object.__setattr__(self, "gin_code", gin_code(self.gin_code))
        require_in_crop_year(self.opened, self.crop_year, "opened")
        if self.closed is not None:
            if self.closed < self.opened:
                raise ValidationError(
                    "closed",
                    f"{self.closed.isoformat()} is before the run opened "
                    f"on {self.opened.isoformat()}",
                )
            require_in_crop_year(self.closed, self.crop_year, "closed")
        object.__setattr__(self, "shift", self.shift.strip())
        object.__setattr__(self, "note", self.note.strip())

    @property
    def is_open(self) -> bool:
        """Whether modules can still be fed into this run."""
        return self.closed is None

    @property
    def hours_span_days(self) -> int:
        """Days the run covered, one for a run that opened and closed the same day."""
        if self.closed is None:
            raise ValidationError("closed", f"gin run {self.ref} is still open")
        return (self.closed - self.opened).days + 1

    def close_on(self, day: date) -> GinRun:
        """The same run, closed on ``day``."""
        if self.closed is not None:
            raise ValidationError("closed", f"gin run {self.ref} closed on {self.closed}")
        return GinRun(
            ref=self.ref,
            crop_year=self.crop_year,
            gin_code=self.gin_code,
            opened=self.opened,
            closed=day,
            shift=self.shift,
            note=self.note,
        )

    def covers(self, day: date) -> bool:
        """Whether ``day`` falls inside the run's open window."""
        if day < self.opened:
            return False
        return self.closed is None or day <= self.closed

    @staticmethod
    def crop_year_for(opened: date) -> int:
        """The crop year a run opening on this day belongs to."""
        return crop_year_of(opened)
