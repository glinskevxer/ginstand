"""Staple length, in thirty seconds of an inch.

The classing office reports upper half mean length as a whole number of 32nds,
so 34 means 34/32 of an inch, or 1.0625. Nobody in a gin office says 1.0625.
They say thirty four, and the loan schedule is keyed on thirty four, so the
whole number is what this package stores.

Fractions of a 32nd exist on the instrument and are thrown away by the office
before the card is issued. This package does the same, and it refuses a value
that arrives with a fraction still on it rather than rounding one silently.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from fractions import Fraction

from ginstand.errors import ValidationError

THIRTY_SECONDS = 32

SHORTEST_STAPLE = 24
"""Three quarters of an inch. Below this the sample is not upland cotton."""

LONGEST_STAPLE = 48
"""An inch and a half. Above this the reading is an instrument fault."""

_INCH_PLACES = Decimal("0.0001")


def check_staple(value: int, field: str = "staple") -> int:
    """Return ``value`` if it is a staple length in whole 32nds, else raise."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(field, "must be a whole number of 32nds")
    if value < SHORTEST_STAPLE:
        raise ValidationError(field, f"must be at least {SHORTEST_STAPLE}/32, got {value}/32")
    if value > LONGEST_STAPLE:
        raise ValidationError(field, f"must be no more than {LONGEST_STAPLE}/32, got {value}/32")
    return value


def to_inches(staple: int) -> Decimal:
    """Staple as a decimal inch, to four places."""
    check_staple(staple)
    return (Decimal(staple) / THIRTY_SECONDS).quantize(_INCH_PLACES, rounding=ROUND_HALF_UP)


def from_inches(inches: Decimal, field: str = "staple") -> int:
    """A decimal inch back to whole 32nds.

    Refuses anything that is not already a whole 32nd. An instrument reading of
    1.05 inches is 33.6/32, and rounding that to 34 quietly moves the bale into
    a different premium band.
    """
    thirty_seconds = Decimal(inches) * THIRTY_SECONDS
    if thirty_seconds != thirty_seconds.to_integral_value():
        raise ValidationError(
            field, f"{inches} in is {thirty_seconds}/32, which is not a whole 32nd"
        )
    return check_staple(int(thirty_seconds), field)


def parse_staple(text: str, field: str = "staple") -> int:
    """Read a staple length the way it is written on a card or typed at a prompt.

    Accepts the bare 32nds the office uses, an explicit fraction, and a decimal
    inch for the rare card that carries one.
    """
    cleaned = text.strip().lower().removesuffix("in").removesuffix('"').strip()
    if not cleaned:
        raise ValidationError(field, "is empty")
    if "/" in cleaned:
        try:
            value = Fraction(cleaned)
        except (ValueError, ZeroDivisionError):
            raise ValidationError(field, f"is not a staple length: {text!r}") from None
        return from_inches(Decimal(value.numerator) / Decimal(value.denominator), field)
    try:
        number = Decimal(cleaned)
    except InvalidOperation:
        raise ValidationError(field, f"is not a staple length: {text!r}") from None
    if number < SHORTEST_STAPLE:
        return from_inches(number, field)
    if number != number.to_integral_value():
        raise ValidationError(field, f"must be a whole number of 32nds, got {text!r}")
    return check_staple(int(number), field)


def format_staple(staple: int) -> str:
    """Staple as it is printed on a report: the 32nds, then the inch in brackets."""
    check_staple(staple)
    whole, part = divmod(staple, THIRTY_SECONDS)
    if part == 0:
        inch = f"{whole} in"
    elif whole == 0:
        inch = f"{part}/32 in"
    else:
        inch = f"{whole} {part}/32 in"
    return f"{staple} ({inch})"
