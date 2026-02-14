"""Recheck requests: asking the classing office to look again.

A gin does not argue with a classing card, it asks for a recheck. The office
pulls the sample, reads it again, and sends back either the same card or a
different one. Both outcomes are worth recording, because a gin whose rechecks
nearly all come back unchanged is a gin whose classer is right and whose office
is being asked too often.

The window matters. A recheck can only be asked for while the sample is still
held, and the office holds samples for a fixed number of days from the date on
the card. Past that there is nothing left to read, so the request is refused
here rather than sent and refused there.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

from ginstand.errors import ValidationError
from ginstand.ids import bale_tag

SAMPLE_HELD_DAYS = 28
"""How long the office keeps a sample after it classes it."""


class RecheckReason(StrEnum):
    """Why the gin thinks the card is wrong."""

    COLOUR = "colour"
    LEAF = "leaf"
    STAPLE = "staple"
    MICRONAIRE = "micronaire"
    EXTRANEOUS = "extraneous matter"
    OTHER = "other"


class RecheckOutcome(StrEnum):
    """What the office did with the request."""

    OPEN = "open"
    """Sent, and nothing has come back."""

    CHANGED = "changed"
    """The office issued a different card."""

    UNCHANGED = "unchanged"
    """The office read the same sample the same way."""

    REFUSED = "refused"
    """The office would not look, usually because the sample was gone."""


@dataclass(frozen=True, slots=True)
class Recheck:
    """One request against one bale's card."""

    tag: str
    requested: date
    reason: RecheckReason
    requested_by: str = ""
    settled: date | None = None
    outcome: RecheckOutcome = RecheckOutcome.OPEN
    note: str = ""
    recheck_id: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "tag", bale_tag(self.tag))
        if self.settled is None and self.outcome is not RecheckOutcome.OPEN:
            raise ValidationError(
                "outcome", f"a request that is still open cannot be {self.outcome}"
            )
        if self.settled is not None:
            if self.outcome is RecheckOutcome.OPEN:
                raise ValidationError("outcome", "a settled request needs an outcome")
            if self.settled < self.requested:
                raise ValidationError(
                    "settled",
                    f"{self.settled.isoformat()} is before the request was made "
                    f"on {self.requested.isoformat()}",
                )
        object.__setattr__(self, "requested_by", self.requested_by.strip())
        object.__setattr__(self, "note", self.note.strip())

    @property
    def open(self) -> bool:
        """Whether the office still has this one."""
        return self.settled is None

    def days_out(self, through: date) -> int:
        """How long the request has been with the office."""
        end = self.settled if self.settled is not None else through
        if end < self.requested:
            raise ValidationError("through", f"{end.isoformat()} is before the request")
        return (end - self.requested).days

    def settle_on(self, day: date, outcome: RecheckOutcome, note: str = "") -> Recheck:
        """The same request, answered."""
        if self.settled is not None:
            raise ValidationError(
                "settled", f"this request was settled on {self.settled.isoformat()}"
            )
        if outcome is RecheckOutcome.OPEN:
            raise ValidationError("outcome", "settling a request needs a real outcome")
        return Recheck(
            tag=self.tag,
            requested=self.requested,
            reason=self.reason,
            requested_by=self.requested_by,
            settled=day,
            outcome=outcome,
            note=note or self.note,
            recheck_id=self.recheck_id,
        )


def sample_held_until(classed: date) -> date:
    """The last day the office will still have the sample."""
    return classed + timedelta(days=SAMPLE_HELD_DAYS)


def within_window(classed: date, on: date) -> bool:
    """Whether a recheck asked for on ``on`` can still be read."""
    return classed <= on <= sample_held_until(classed)
