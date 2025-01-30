"""Moisture content, wet basis, as a percentage to one decimal place.

Wet basis means the water is measured against the total weight, not against the
dry matter. It is the convention on every meter in a gin, and it matters here
because a weight quoted at one moisture and a weight quoted at another are not
the same cotton unless the dry weight is carried between them.

One decimal place is what the meters read. Two would be inventing precision the
instrument does not have.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from ginstand.errors import ValidationError

SAFE_BALE_MOISTURE = Decimal("7.5")
"""Above this a bale heats in the warehouse. It is the ceiling on restoration."""

DRY_GINNING_FLOOR = Decimal("5.0")
"""Below this the fibre breaks at the gin stand and the staple reading drops."""

DRYER_THRESHOLD = Decimal("8.0")
"""Seed cotton above this goes through the dryers before the stands."""

MAX_MOISTURE = Decimal("25.0")
"""A meter reading past this is a wet spot or a fault, not a module."""

_PLACES = Decimal("0.1")


def moisture(value: Decimal | str | int, field: str = "moisture") -> Decimal:
    """A moisture reading, quantised to the one place a meter reports."""
    try:
        reading = Decimal(value)
    except (InvalidOperation, ValueError):
        raise ValidationError(field, f"is not a number: {value!r}") from None
    reading = reading.quantize(_PLACES, rounding=ROUND_HALF_UP)
    if reading < 0:
        raise ValidationError(field, f"must not be negative, got {reading}")
    if reading > MAX_MOISTURE:
        raise ValidationError(field, f"must be no more than {MAX_MOISTURE}%, got {reading}")
    return reading


def dry_weight(pounds: int, at_moisture: Decimal) -> int:
    """The weight of the dry matter in ``pounds`` of cotton at that moisture.

    This is the quantity that survives drying and restoration. Every weight
    comparison across two moisture readings goes through it.
    """
    if pounds < 0:
        raise ValidationError("weight", "must not be negative")
    reading = moisture(at_moisture)
    dry = Decimal(pounds) * (100 - reading) / 100
    return int(dry.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def weight_at(dry_pounds: int, at_moisture: Decimal) -> int:
    """What ``dry_pounds`` of dry matter weighs once it holds that moisture."""
    if dry_pounds < 0:
        raise ValidationError("weight", "must not be negative")
    reading = moisture(at_moisture)
    if reading >= 100:
        raise ValidationError("moisture", "cannot be 100% or more on a wet basis")
    wet = Decimal(dry_pounds) * 100 / (100 - reading)
    return int(wet.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def reweigh(pounds: int, from_moisture: Decimal, to_moisture: Decimal) -> int:
    """The same cotton weighed again after its moisture moved."""
    return weight_at(dry_weight(pounds, from_moisture), to_moisture)


def water_added(pounds: int, from_moisture: Decimal, to_moisture: Decimal) -> int:
    """Pounds of water between two moisture readings of the same cotton.

    Negative when the cotton dried out, which is the ordinary case for a module
    sitting in the yard through a dry week.
    """
    return reweigh(pounds, from_moisture, to_moisture) - pounds


def safe_to_store(at_moisture: Decimal | str | int) -> bool:
    """Whether a bale at this moisture can go to the warehouse as it is."""
    return moisture(at_moisture) <= SAFE_BALE_MOISTURE


def needs_drying(at_moisture: Decimal | str | int) -> bool:
    """Whether seed cotton at this moisture goes through the dryers."""
    return moisture(at_moisture) > DRYER_THRESHOLD


def too_dry_to_gin(at_moisture: Decimal | str | int) -> bool:
    """Whether seed cotton at this moisture will break rather than gin."""
    return moisture(at_moisture) < DRY_GINNING_FLOOR


def format_moisture(at_moisture: Decimal | str | int) -> str:
    """A reading as it is printed on a ticket."""
    return f"{moisture(at_moisture)}%"
