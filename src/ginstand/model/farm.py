"""Farms and fields.

A field is the smallest thing the gin tracks cotton back to. Modules carry a
field, bales carry the modules they came from, and a producer asking why one
lot classed worse than another is asking a question about fields.

Acres matter because the office prints a yield per acre on the settlement, and
a producer checks that number before they check anything else.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ginstand.errors import ValidationError
from ginstand.ids import reference

MAX_FIELD_ACRES = Decimal("5000")
"""Bigger than this is a farm typed into a field record."""

_ACRE_PLACES = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class Farm:
    """A farm, as the office and the farm agency both know it."""

    ref: str
    producer: str
    name: str
    fsa_number: str = ""
    county: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "ref", reference(self.ref, "farm"))
        object.__setattr__(self, "producer", reference(self.producer, "producer"))
        cleaned = self.name.strip()
        if not cleaned:
            raise ValidationError("farm name", "is empty")
        object.__setattr__(self, "name", cleaned)
        object.__setattr__(self, "fsa_number", self.fsa_number.strip().upper())
        object.__setattr__(self, "county", self.county.strip())


@dataclass(frozen=True, slots=True)
class Field:
    """A field on a farm, with the acres and the lease it is farmed under."""

    ref: str
    farm: str
    name: str
    acres: Decimal
    lease: str
    variety: str = ""
    irrigated: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "ref", reference(self.ref, "field"))
        object.__setattr__(self, "farm", reference(self.farm, "farm"))
        object.__setattr__(self, "lease", reference(self.lease, "lease"))
        cleaned = self.name.strip()
        if not cleaned:
            raise ValidationError("field name", "is empty")
        object.__setattr__(self, "name", cleaned)
        acres = Decimal(self.acres).quantize(_ACRE_PLACES, rounding=ROUND_HALF_UP)
        if acres <= 0:
            raise ValidationError("acres", f"must be above zero, got {acres}")
        if acres > MAX_FIELD_ACRES:
            raise ValidationError("acres", f"must be no more than {MAX_FIELD_ACRES}, got {acres}")
        object.__setattr__(self, "acres", acres)
        object.__setattr__(self, "variety", self.variety.strip())

    def yield_per_acre(self, bales: int) -> Decimal:
        """Bales per acre off this field, to two places."""
        if bales < 0:
            raise ValidationError("bales", "must not be negative")
        return (Decimal(bales) / self.acres).quantize(_ACRE_PLACES, rounding=ROUND_HALF_UP)

    def lint_per_acre(self, lint_pounds: int) -> Decimal:
        """Pounds of lint per acre off this field, to one place."""
        if lint_pounds < 0:
            raise ValidationError("lint", "must not be negative")
        return (Decimal(lint_pounds) / self.acres).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
