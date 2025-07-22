"""Valuing a lot: several bales priced together.

A producer is paid on a lot, not on a bale, and the lot's average rate is the
number they compare against the neighbour's. It has to be a weighted average.
An unweighted one over eight bales is out by a few points, which sounds like
nothing and is a dollar or two a bale, and a producer who works it out by hand
gets a different answer from the gin.

Refused bales are counted and named rather than dropped. A lot of forty bales
with two off the schedule is a different conversation from a lot of thirty
eight, and the statement has to be able to have it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ginstand.errors import ValidationError
from ginstand.loan.schedule import Schedule
from ginstand.loan.value import Valuation, value_bale
from ginstand.model.classing import Classing
from ginstand.units.money import Money, format_money


@dataclass(frozen=True, slots=True)
class LotValue:
    """Several bales valued together."""

    valuations: tuple[Valuation, ...]

    @property
    def bales(self) -> int:
        """How many bales are in the lot."""
        return len(self.valuations)

    @property
    def taken(self) -> tuple[Valuation, ...]:
        """The bales the loan will take."""
        return tuple(v for v in self.valuations if v.eligible)

    @property
    def refused(self) -> tuple[Valuation, ...]:
        """The bales the loan will not take."""
        return tuple(v for v in self.valuations if not v.eligible)

    @property
    def net_pounds(self) -> int:
        """Lint in the whole lot."""
        return sum(v.net_pounds for v in self.valuations)

    @property
    def taken_pounds(self) -> int:
        """Lint in the bales the loan will take."""
        return sum(v.net_pounds for v in self.taken)

    @property
    def value(self) -> Money:
        """What the loan pays for the lot."""
        return Money(sum(v.value for v in self.valuations))

    @property
    def average_rate(self) -> Decimal:
        """Cents per pound across the bales taken, weighted by weight.

        Raises rather than returning zero when nothing was taken. A lot with no
        eligible bales has no rate, and printing 0.00c reads as a rate of zero.
        """
        if not self.taken:
            raise ValidationError("lot", "has no bales the loan will take, so it has no rate")
        return (Decimal(self.value) / Decimal(self.taken_pounds)).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

    @property
    def refusals(self) -> dict[str, int]:
        """How many bales each refusal reason accounts for."""
        counts: dict[str, int] = {}
        for valuation in self.refused:
            counts[valuation.refusal] = counts.get(valuation.refusal, 0) + 1
        return counts

    @property
    def line(self) -> str:
        """The line a lot list prints."""
        refused = f", {len(self.refused)} refused" if self.refused else ""
        return f"{self.bales} bales{refused}  {self.net_pounds:,} lb  {format_money(self.value)}"


def value_lot(
    schedule: Schedule,
    cards: Sequence[tuple[Classing, int]],
    enrolled: bool = True,
) -> LotValue:
    """Value a lot of bales, each given with its net weight."""
    if not cards:
        raise ValidationError("lot", "has no bales in it")
    return LotValue(
        valuations=tuple(
            value_bale(schedule, card, net_pounds, enrolled) for card, net_pounds in cards
        )
    )
