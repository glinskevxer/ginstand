"""Bands, and reading a value off one.

Every table in the loan schedule except the colour and leaf ones is a ladder of
bands: a range of some measurement, and the points that apply inside it. Bands
are half open at the top so that a reading on a boundary belongs to exactly one
of them, and the ladder is checked on construction to make sure it covers its
whole range with no gap and no overlap.

That check is worth its cost. A gap in a mic ladder is a bale that cannot be
priced, and it will not be found until the one bale in a season that lands in
the gap turns up on a settlement.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise

from ginstand.errors import ScheduleError, ValidationError

Points = Decimal
"""Hundredths of a cent per pound."""


@dataclass(frozen=True, slots=True)
class Band:
    """One rung of a ladder: from ``low`` up to but not including ``high``."""

    low: Decimal
    high: Decimal
    points: Points
    label: str = ""

    def __post_init__(self) -> None:
        if self.high <= self.low:
            raise ValidationError(
                "band", f"{self.low} to {self.high} is empty or the wrong way round"
            )

    def holds(self, value: Decimal) -> bool:
        """Whether a reading falls in this band."""
        return self.low <= value < self.high

    @property
    def name(self) -> str:
        """The band as a schedule prints it."""
        return self.label or f"{self.low} to {self.high}"


class Ladder:
    """An ordered set of bands covering a range with no gap and no overlap."""

    def __init__(self, name: str, bands: Sequence[Band]) -> None:
        if not bands:
            raise ValidationError(name, "has no bands in it")
        ordered = sorted(bands, key=lambda band: band.low)
        for first, second in pairwise(ordered):
            if first.high < second.low:
                raise ValidationError(name, f"has a gap between {first.high} and {second.low}")
            if first.high > second.low:
                raise ValidationError(name, f"overlaps between {second.low} and {first.high}")
        self.name = name
        self.bands = tuple(ordered)

    @property
    def low(self) -> Decimal:
        """The bottom of the range this ladder covers."""
        return self.bands[0].low

    @property
    def high(self) -> Decimal:
        """The top of the range this ladder covers, exclusive."""
        return self.bands[-1].high

    def band_for(self, value: Decimal) -> Band:
        """The band a reading falls in. Raises if the ladder does not cover it."""
        for band in self.bands:
            if band.holds(value):
                return band
        raise ScheduleError(
            f"the {self.name} schedule runs {self.low} to {self.high} and does not cover {value}"
        )

    def points_for(self, value: Decimal) -> Points:
        """The points that apply at a reading."""
        return self.band_for(value).points

    def __len__(self) -> int:
        return len(self.bands)
