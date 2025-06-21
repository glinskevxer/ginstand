"""Moisture restoration at the press, and the cap on it.

Ginning dries cotton out. Lint coming off the stands is drier than it wants to
be, which costs weight the producer is paid for and makes the bale harder to
press. So water goes back in at the press. That is legitimate and every gin does
it, and it is also the easiest place in a gin to take money that is not yours,
so it is capped in two directions at once.

The first cap is the storage ceiling: a bale above it heats in the warehouse
whatever anybody wanted. The second is a fraction of the bale's weight at the
press, so the pounds of water allowed move with the bale.

Worth knowing, and tested below because it is not obvious: the second cap does
not actually restrict the moisture reachable. Water added as a fraction of the
pressed weight works out to the same percentage move on a four hundred pound
bale as on a six hundred pound one. The cap bites in pounds, not in points.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from ginstand.errors import ValidationError
from ginstand.units.moisture import SAFE_BALE_MOISTURE, moisture, reweigh

MAX_ADDED_FRACTION = Decimal("0.020")
"""Water added may not exceed this fraction of the bale's weight at the press."""


@dataclass(frozen=True, slots=True)
class Restoration:
    """What restoring a bale from one moisture to another would do."""

    pressed_pounds: int
    from_moisture: Decimal
    to_moisture: Decimal
    final_pounds: int
    allowed_pounds: int

    @property
    def added_pounds(self) -> int:
        """Water that would go in."""
        return self.final_pounds - self.pressed_pounds

    @property
    def within_cap(self) -> bool:
        """Whether the water is inside the fraction of pressed weight allowed."""
        return self.added_pounds <= self.allowed_pounds

    @property
    def storable(self) -> bool:
        """Whether the bale would still be under the storage ceiling."""
        return self.to_moisture <= SAFE_BALE_MOISTURE

    @property
    def allowed(self) -> bool:
        """Whether this restoration can be done at all."""
        return self.within_cap and self.storable

    @property
    def refusal(self) -> str:
        """Why it cannot be done, or an empty string if it can."""
        if not self.storable:
            return f"{self.to_moisture}% is above the storage ceiling of {SAFE_BALE_MOISTURE}%"
        if not self.within_cap:
            return (
                f"{self.added_pounds} lb of water is more than the "
                f"{self.allowed_pounds} lb allowed on a {self.pressed_pounds} lb bale"
            )
        return ""


def cap_pounds(pressed_pounds: int) -> int:
    """The most water that may go into a bale of this weight, rounded down."""
    if pressed_pounds <= 0:
        raise ValidationError("pressed weight", "must be above zero")
    return int(
        (Decimal(pressed_pounds) * MAX_ADDED_FRACTION).quantize(Decimal("1"), rounding=ROUND_DOWN)
    )


def plan(pressed_pounds: int, from_moisture: Decimal, to_moisture: Decimal) -> Restoration:
    """Work out what taking a bale from one moisture to another would take."""
    start = moisture(from_moisture, "moisture at the press")
    target = moisture(to_moisture, "target moisture")
    if target < start:
        raise ValidationError(
            "target moisture",
            f"{target}% is below the {start}% the bale came off at, which is drying",
        )
    return Restoration(
        pressed_pounds=pressed_pounds,
        from_moisture=start,
        to_moisture=target,
        final_pounds=reweigh(pressed_pounds, start, target),
        allowed_pounds=cap_pounds(pressed_pounds),
    )


def highest_allowed(pressed_pounds: int, from_moisture: Decimal) -> Decimal:
    """The wettest a bale may be taken to, given where it came off the press.

    Walks the tenths rather than solving it, because the cap is stated in whole
    pounds of water and the answer has to be a moisture the press can actually
    dial in.
    """
    start = moisture(from_moisture, "moisture at the press")
    best = start
    target = start
    while target < SAFE_BALE_MOISTURE:
        target = (target + Decimal("0.1")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        if not plan(pressed_pounds, start, target).allowed:
            break
        best = target
    return best
