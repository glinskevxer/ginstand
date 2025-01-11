"""Weights, in whole pounds.

The gin scale reads whole pounds and every ticket is written in whole pounds, so
that is what this package stores. Hundredweight shows up on the ginning tariff
and in the seed contract, and it is derived on the way out rather than kept.

Rounding rule, applied everywhere: pounds are exact integers, and anything that
divides pounds rounds half up at the last step only. There is no float here.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from ginstand.errors import ValidationError

POUNDS_PER_CWT = 100
"""Hundredweight. The ginning tariff and the seed contract both price per cwt."""

MAX_TICKET_POUNDS = 200_000
"""Refuse anything past a loaded truck and trailer. A scale that reads higher
than this has a fault, and a fault read into the book is worse than a refusal."""

_CWT = Decimal(POUNDS_PER_CWT)


def check_pounds(
    value: int,
    field: str,
    *,
    minimum: int = 0,
    maximum: int = MAX_TICKET_POUNDS,
) -> int:
    """Return ``value`` if it is a sane weight in pounds, else raise.

    ``bool`` is rejected outright. It is an ``int`` to Python and it is never a
    weight, and letting it through turns a wrong argument into a silent zero.
    """
    if isinstance(value, bool):
        raise ValidationError(field, "must be a whole number of pounds")
    if not isinstance(value, int):
        raise ValidationError(field, "must be a whole number of pounds")
    if value < minimum:
        raise ValidationError(field, f"must be at least {minimum} lb, got {value}")
    if value > maximum:
        raise ValidationError(field, f"must be no more than {maximum} lb, got {value}")
    return value


def net_of(gross: int, tare: int, *, field: str = "net weight") -> int:
    """Net weight from a gross and a tare reading.

    A tare heavier than the gross is a ticket written the wrong way round, which
    happens often enough on a busy scale to be worth naming.
    """
    check_pounds(gross, "gross weight")
    check_pounds(tare, "tare weight")
    if tare > gross:
        raise ValidationError(
            field, f"tare {tare} lb is heavier than gross {gross} lb, check the ticket"
        )
    return gross - tare


def to_cwt(pounds: int) -> Decimal:
    """Pounds as hundredweight, to two places."""
    check_pounds(pounds, "weight")
    return (Decimal(pounds) / _CWT).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def from_cwt(hundredweight: Decimal) -> int:
    """Hundredweight back to whole pounds, rounded half up."""
    if hundredweight < 0:
        raise ValidationError("weight", "must not be negative")
    return int((hundredweight * _CWT).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def parse_pounds(text: str, field: str = "weight") -> int:
    """Read a weight off a ticket or a command line.

    Accepts thousands separators and a trailing unit, because both turn up when
    a weight is copied off a scale printout by hand.
    """
    cleaned = text.strip().lower().removesuffix("lbs").removesuffix("lb").strip()
    cleaned = cleaned.replace(",", "").replace(" ", "")
    if not cleaned:
        raise ValidationError(field, "is empty")
    try:
        value = int(cleaned)
    except ValueError:
        raise ValidationError(field, f"is not a whole number of pounds: {text!r}") from None
    return check_pounds(value, field)


def format_pounds(pounds: int) -> str:
    """Weight as it is printed on a report, with a thousands separator."""
    return f"{pounds:,} lb"
