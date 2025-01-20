"""Money, held as whole cents.

Cotton is priced in cents per pound and the schedules adjust that price in
points, which are hundredths of a cent. A bale is around 500 pounds, so a point
is worth five cents on a bale and around fifty dollars on a hundred bale lot.
That is real money to a producer, so rates keep four decimal places and only the
final amount is rounded to a cent.

Amounts are ``int`` cents and may be negative: a settlement line for a ginning
charge is a negative amount, not a positive one wearing a sign somewhere else.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import NewType

from ginstand.errors import ValidationError

Money = NewType("Money", int)
"""An amount in whole cents. Negative means the producer owes it."""

ZERO = Money(0)

_CENT = Decimal("0.01")
_RATE_PLACES = Decimal("0.0001")


def money(dollars: Decimal | str | int) -> Money:
    """An amount from a figure in dollars, rounded half up to the cent."""
    try:
        value = Decimal(dollars)
    except (InvalidOperation, ValueError):
        raise ValidationError("amount", f"is not a number: {dollars!r}") from None
    cents = (value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return Money(int(cents))


def to_dollars(amount: Money) -> Decimal:
    """The amount in dollars, exact, with two places."""
    return (Decimal(amount) / 100).quantize(_CENT)


def rate(cents_per_pound: Decimal | str) -> Decimal:
    """A price in cents per pound, held to four places.

    Four places is one point of a point. The loan schedules are published to two
    places and the intermediate arithmetic needs the room underneath.
    """
    try:
        value = Decimal(cents_per_pound)
    except (InvalidOperation, ValueError):
        raise ValidationError("rate", f"is not a number: {cents_per_pound!r}") from None
    return value.quantize(_RATE_PLACES, rounding=ROUND_HALF_UP)


def at_rate(pounds: int, cents_per_pound: Decimal) -> Money:
    """What ``pounds`` is worth at a price in cents per pound.

    Rounded to the cent once, at the end. Rounding per pound instead would move
    a hundred bale lot by several dollars.
    """
    if pounds < 0:
        raise ValidationError("weight", "must not be negative")
    total_cents = Decimal(pounds) * cents_per_pound
    return Money(int(total_cents.quantize(Decimal("1"), rounding=ROUND_HALF_UP)))


def share_of(amount: Money, fraction: Decimal) -> Money:
    """A fraction of an amount, rounded half up to the cent.

    The complement is deliberately not derived here. A lease split has to add
    back to the whole, and that is the caller's job to arrange rather than
    something two independent roundings can be trusted to do.
    """
    if fraction < 0 or fraction > 1:
        raise ValidationError("share", f"must be between 0 and 1, got {fraction}")
    return Money(int((Decimal(amount) * fraction).quantize(Decimal("1"), rounding=ROUND_HALF_UP)))


def parse_money(text: str, field: str = "amount") -> Money:
    """Read an amount off a statement or a command line."""
    cleaned = text.strip().replace("$", "").replace(",", "").replace(" ", "")
    negative = cleaned.startswith("(") and cleaned.endswith(")")
    if negative:
        cleaned = cleaned[1:-1]
    if not cleaned:
        raise ValidationError(field, "is empty")
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        raise ValidationError(field, f"is not an amount: {text!r}") from None
    amount = money(value)
    return Money(-amount) if negative else amount


def format_money(amount: Money) -> str:
    """An amount as it is printed on a statement."""
    sign = "-" if amount < 0 else ""
    whole, cents = divmod(abs(amount), 100)
    return f"{sign}${whole:,}.{cents:02d}"


def format_rate(cents_per_pound: Decimal) -> str:
    """A price as it is printed on a schedule, in cents per pound."""
    return f"{cents_per_pound.quantize(_CENT, rounding=ROUND_HALF_UP)}c"
