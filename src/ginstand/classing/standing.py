"""Whether a bale is on the schedule at all, and why not when it is not.

Three things put a bale off the schedule and only two of them are on the card.
Colour rank eight and leaf grade eight are the classing office's judgement.
Heavy plastic is ours: the card notes it as extraneous matter and prices it, and
this gin does not sell a bale with heavy plastic in it at any price, because a
mill that finds film in a bale stops buying from the gin that shipped it.

Keeping our rule and the office's apart is the point of this module. A bale off
the schedule for our reason can be argued about internally. One off for the
office's reason cannot be argued about at all. A settlement that cannot say
which of those happened is a settlement nobody can answer questions about.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ginstand.grades.matter import ExtraneousKind, ExtraneousLevel
from ginstand.model.classing import Classing


class OffSchedule(StrEnum):
    """A reason a bale is not priced off the premium and discount tables."""

    COLOUR = "colour below grade"
    """The card graded the colour rank eight."""

    LEAF = "leaf below grade"
    """The card graded the leaf eight."""

    PLASTIC = "heavy plastic"
    """The classer found plastic at the heavy level. This is the gin's own rule."""


CONDEMNING_PLASTIC = ExtraneousLevel.HEAVY
"""The level of plastic this gin will not ship at any price."""


@dataclass(frozen=True, slots=True)
class Standing:
    """Where a bale stands against the schedule."""

    tag: str
    reasons: tuple[OffSchedule, ...]

    @property
    def on_schedule(self) -> bool:
        """Whether the premium and discount tables apply to this bale."""
        return not self.reasons

    @property
    def below_grade(self) -> bool:
        """Whether the bale is off the schedule for any reason."""
        return bool(self.reasons)

    @property
    def carded_reasons(self) -> tuple[OffSchedule, ...]:
        """The reasons the classing office is responsible for."""
        return tuple(r for r in self.reasons if r is not OffSchedule.PLASTIC)

    @property
    def gin_reasons(self) -> tuple[OffSchedule, ...]:
        """The reasons this gin applied itself."""
        return tuple(r for r in self.reasons if r is OffSchedule.PLASTIC)

    @property
    def arguable(self) -> bool:
        """Whether every reason is one of ours, so the office has not condemned it."""
        return self.below_grade and not self.carded_reasons

    @property
    def line(self) -> str:
        """The line a bale list prints for this bale."""
        if self.on_schedule:
            return f"{self.tag}  on schedule"
        return f"{self.tag}  off schedule: {', '.join(str(r) for r in self.reasons)}"


def standing_of(card: Classing) -> Standing:
    """Work out where a bale stands from its card."""
    reasons = []
    if card.color.below_grade:
        reasons.append(OffSchedule.COLOUR)
    if card.leaf == 8:
        reasons.append(OffSchedule.LEAF)
    if _heavy_plastic(card):
        reasons.append(OffSchedule.PLASTIC)
    return Standing(tag=card.tag, reasons=tuple(reasons))


def _heavy_plastic(card: Classing) -> bool:
    return any(
        note.kind is ExtraneousKind.PLASTIC and note.level is CONDEMNING_PLASTIC
        for note in card.extraneous
    )


def loan_eligible(card: Classing, enrolled: bool) -> bool:
    """Whether a bale can go into the CCC loan.

    Two things have to hold and they come from different places. The bale has to
    be on the schedule, which is about the cotton, and the producer has to be
    enrolled, which is about paperwork filed months earlier.
    """
    return enrolled and standing_of(card).on_schedule
