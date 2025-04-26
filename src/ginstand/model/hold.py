"""Holds on a module in the yard.

A hold is a reason not to gin something yet. It is placed by a person, it names
why, and it stays until somebody lifts it. Holds are separate records rather
than a flag on the module because the gin has to be able to say later who held
what and for how long: a producer whose cotton sat for three weeks asks, and
"it was wet" is not an answer unless the book says who decided that and when.

A module has at most one hold open at a time. Two people holding the same module
for different reasons is a conversation, not a data structure.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from ginstand.errors import ValidationError
from ginstand.ids import reference


class HoldReason(StrEnum):
    """Why a module is not going into a run yet."""

    WET = "wet"
    """Over the dryer's range. It goes back out to lose moisture."""

    PLASTIC = "plastic"
    """Wrap damage. It gets picked over before it goes anywhere near a stand."""

    CONTAMINATION = "contamination"
    """Something else in the module: twine, a jacket, a piece of the picker."""

    WEIGHT = "weight"
    """The ticket is disputed and the module is not ginned until it is settled."""

    IDENTITY = "identity"
    """The tag does not match the paperwork. Ginning it loses whose it was."""

    OTHER = "other"


@dataclass(frozen=True, slots=True)
class Hold:
    """One hold, open or lifted."""

    module: str
    reason: HoldReason
    placed: date
    placed_by: str = ""
    lifted: date | None = None
    lifted_by: str = ""
    note: str = ""
    hold_id: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "module", reference(self.module, "module tag"))
        if self.lifted is not None and self.lifted < self.placed:
            raise ValidationError(
                "lifted",
                f"{self.lifted.isoformat()} is before the hold was placed "
                f"on {self.placed.isoformat()}",
            )
        if self.lifted is None and self.lifted_by.strip():
            raise ValidationError("lifted_by", "a hold that is still open was not lifted by anyone")
        object.__setattr__(self, "placed_by", self.placed_by.strip())
        object.__setattr__(self, "lifted_by", self.lifted_by.strip())
        object.__setattr__(self, "note", self.note.strip())

    @property
    def open(self) -> bool:
        """Whether this hold is still stopping the module."""
        return self.lifted is None

    def days_held(self, through: date) -> int:
        """How long the module has been held, counting to ``through`` if still open."""
        end = self.lifted if self.lifted is not None else through
        if end < self.placed:
            raise ValidationError("through", f"{end.isoformat()} is before the hold was placed")
        return (end - self.placed).days

    def lift_on(self, day: date, by: str = "") -> Hold:
        """The same hold, lifted."""
        if self.lifted is not None:
            raise ValidationError("lifted", f"this hold was lifted on {self.lifted.isoformat()}")
        return Hold(
            module=self.module,
            reason=self.reason,
            placed=self.placed,
            placed_by=self.placed_by,
            lifted=day,
            lifted_by=by,
            note=self.note,
            hold_id=self.hold_id,
        )
