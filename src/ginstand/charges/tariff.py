"""The published ginning tariff, and billing a quantity against it.

A tariff line is a rate and what the rate is charged against. There are only
four bases and they are not interchangeable: ginning goes on hundredweight of
seed cotton, bagging and ties go on bales, hauling goes on modules, and the
classing fee is per bale because the office charges the gin per sample.

Charging ginning per bale instead of per hundredweight is the single most
common way a gin's income drifts from its costs. A low turnout lot makes fewer
bales from the same seed cotton and takes the same time on the stands, so a per
bale rate undercharges exactly the lots that cost most to gin. The basis is
therefore part of the tariff rather than something the biller decides.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from ginstand.errors import ValidationError
from ginstand.units.money import Money, format_money
from ginstand.units.weight import to_cwt


class Basis(StrEnum):
    """What a rate is charged against."""

    PER_CWT = "per cwt of seed cotton"
    PER_BALE = "per bale"
    PER_MODULE = "per module"
    FLAT = "flat"


@dataclass(frozen=True, slots=True)
class TariffLine:
    """One published rate."""

    code: str
    description: str
    basis: Basis
    rate: Money
    optional: bool = False
    """Whether the line is only charged when the service was asked for."""

    def __post_init__(self) -> None:
        cleaned = self.code.strip().upper()
        if not cleaned:
            raise ValidationError("charge code", "is empty")
        object.__setattr__(self, "code", cleaned)
        if not self.description.strip():
            raise ValidationError("charge description", "is empty")
        object.__setattr__(self, "description", self.description.strip())
        if self.rate < 0:
            raise ValidationError("rate", f"must not be negative, got {self.rate}")


@dataclass(frozen=True, slots=True)
class Tariff:
    """A crop year's published charges."""

    crop_year: int
    lines: tuple[TariffLine, ...]

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for line in self.lines:
            if line.code in seen:
                raise ValidationError("tariff", f"has two lines coded {line.code}")
            seen.add(line.code)

    def line(self, code: str) -> TariffLine:
        """One line off the tariff."""
        wanted = code.strip().upper()
        for line in self.lines:
            if line.code == wanted:
                return line
        raise ValidationError("charge code", f"{wanted} is not on the {self.crop_year} tariff")

    @property
    def codes(self) -> tuple[str, ...]:
        """Every code on the tariff, in the order published."""
        return tuple(line.code for line in self.lines)


@dataclass(frozen=True, slots=True)
class Charge:
    """One line of a bill: a rate, a quantity, and what they came to."""

    code: str
    description: str
    basis: Basis
    units: Decimal
    rate: Money
    amount: Money

    @property
    def text(self) -> str:
        """The line as it prints on a bill."""
        return (
            f"{self.code:<6} {self.description:<28} {self.units:>10} "
            f"{format_money(self.rate):>10} {format_money(self.amount):>12}"
        )


@dataclass(frozen=True, slots=True)
class Bill:
    """Every charge against one producer's share of a run."""

    charges: tuple[Charge, ...]

    @property
    def total(self) -> Money:
        """What the gin is owed."""
        return Money(sum(charge.amount for charge in self.charges))

    def amount_for(self, code: str) -> Money:
        """One line's amount, or zero if the line was not charged."""
        wanted = code.strip().upper()
        for charge in self.charges:
            if charge.code == wanted:
                return charge.amount
        return Money(0)

    @property
    def lines(self) -> tuple[str, ...]:
        """The bill as printed lines."""
        return tuple(charge.text for charge in self.charges)


def units_for(basis: Basis, bales: int, seed_cotton_pounds: int, modules: int) -> Decimal:
    """How many units a basis counts, given the quantities off a run share."""
    if basis is Basis.PER_BALE:
        return Decimal(bales)
    if basis is Basis.PER_MODULE:
        return Decimal(modules)
    if basis is Basis.PER_CWT:
        return to_cwt(seed_cotton_pounds)
    return Decimal(1)


def bill(
    tariff: Tariff,
    *,
    bales: int,
    seed_cotton_pounds: int,
    modules: int,
    extras: Sequence[str] = (),
) -> Bill:
    """Bill one producer's share of a run against the tariff."""
    if bales < 0 or seed_cotton_pounds < 0 or modules < 0:
        raise ValidationError("quantity", "must not be negative")
    wanted = {code.strip().upper() for code in extras}
    for code in wanted:
        tariff.line(code)
    charges = []
    for line in tariff.lines:
        if line.optional and line.code not in wanted:
            continue
        units = units_for(line.basis, bales, seed_cotton_pounds, modules)
        amount = Money(
            int((units * Decimal(line.rate)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        )
        charges.append(
            Charge(
                code=line.code,
                description=line.description,
                basis=line.basis,
                units=units,
                rate=line.rate,
                amount=amount,
            )
        )
    return Bill(charges=tuple(charges))
