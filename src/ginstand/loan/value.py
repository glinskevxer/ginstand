"""What a bale is worth against the loan, and the working that got there.

The value is one multiplication at the end, and everything before it is reading
five tables. The working is kept because a producer who disagrees with a
settlement disagrees with one line of it, and a number with no lines behind it
cannot be discussed, only accepted or refused.

A bale off the schedule is valued at nothing rather than at a large discount.
That is not the same as a bale worth nothing: it is a bale the loan does not
take, which the producer sells some other way.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ginstand.classing.standing import Standing, standing_of
from ginstand.loan.points import Points
from ginstand.loan.schedule import Schedule
from ginstand.model.classing import Classing
from ginstand.units.money import Money, at_rate, format_money, format_rate

MINIMUM_RATE = Decimal("0.0000")
"""A bale is never worth a negative amount, however far the discounts run."""


@dataclass(frozen=True, slots=True)
class Line:
    """One table's contribution to a bale's rate."""

    name: str
    reading: str
    points: Points

    @property
    def text(self) -> str:
        """The line as it prints on a valuation."""
        sign = "+" if self.points > 0 else ""
        return f"{self.name:<12} {self.reading:>8}  {sign}{self.points}"


@dataclass(frozen=True, slots=True)
class Valuation:
    """A bale's loan value, with every line that made it."""

    tag: str
    net_pounds: int
    base_rate: Decimal
    lines: tuple[Line, ...]
    standing: Standing
    enrolled: bool

    @property
    def eligible(self) -> bool:
        """Whether the loan will take this bale."""
        return self.enrolled and self.standing.on_schedule

    @property
    def total_points(self) -> Points:
        """Every premium and discount added together."""
        return sum((line.points for line in self.lines), Decimal("0"))

    @property
    def rate(self) -> Decimal:
        """Cents per pound after the tables, floored at zero."""
        if not self.eligible:
            return MINIMUM_RATE
        adjusted = self.base_rate + self.total_points / 100
        return max(adjusted, MINIMUM_RATE)

    @property
    def value(self) -> Money:
        """What the loan pays on this bale."""
        return at_rate(self.net_pounds, self.rate)

    @property
    def refusal(self) -> str:
        """Why the loan will not take it, or an empty string."""
        if self.standing.below_grade:
            return ", ".join(str(reason) for reason in self.standing.reasons)
        if not self.enrolled:
            return "the producer is not enrolled for the loan"
        return ""

    @property
    def summary(self) -> str:
        """The one line a bale list prints."""
        if not self.eligible:
            return f"{self.tag}  no loan value: {self.refusal}"
        return (
            f"{self.tag}  {self.net_pounds} lb at {format_rate(self.rate)}  "
            f"{format_money(self.value)}"
        )

    @property
    def working(self) -> tuple[str, ...]:
        """The valuation as the lines a statement prints."""
        rows = [f"{'base':<12} {'':>8}  {self.base_rate}"]
        rows.extend(line.text for line in self.lines)
        rows.append(f"{'rate':<12} {'':>8}  {self.rate}")
        return tuple(rows)


def value_bale(
    schedule: Schedule,
    card: Classing,
    net_pounds: int,
    enrolled: bool = True,
) -> Valuation:
    """Value one bale against a crop year's schedule."""
    standing = standing_of(card)
    if standing.below_grade or not enrolled:
        return Valuation(
            tag=card.tag,
            net_pounds=net_pounds,
            base_rate=schedule.base_rate,
            lines=(),
            standing=standing,
            enrolled=enrolled,
        )
    lines = (
        Line("colour", str(card.color.code), schedule.colour_points(card.color)),
        Line("leaf", str(card.leaf), schedule.leaf_points(card.leaf)),
        Line("staple", str(card.staple), schedule.staple_points(card.color, card.staple)),
        Line("micronaire", str(card.micronaire), schedule.micronaire_points(card.micronaire)),
        Line("strength", str(card.strength), schedule.strength_points(card.strength)),
        Line("uniformity", str(card.uniformity), schedule.uniformity_points(card.uniformity)),
    )
    return Valuation(
        tag=card.tag,
        net_pounds=net_pounds,
        base_rate=schedule.base_rate,
        lines=lines,
        standing=standing,
        enrolled=enrolled,
    )
