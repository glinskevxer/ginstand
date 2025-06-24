"""Reading a colour grade off the gin's own colorimeter.

The classing office is the authority on colour, and its card arrives days after
the bale does. In between, the gin has its own instrument and wants to sort
bales into rough lots before they ship. That is what this is for, and it is not
for anything else: nothing downstream of here prices an estimate.

The instrument gives two numbers. Rd is reflectance, how bright the sample is,
and it runs from about forty on grey cotton to the mid eighties on the best
white. Plus b is yellowness. The chart is read the same way round every time:
plus b picks the column, Rd picks the row.

The boundaries below are this gin's own reading of the chart. They are close to
the office's and they are not the office's, so the estimate is expected to
disagree with the card sometimes. The comparison is offered rather than hidden,
because a gin whose instrument drifts wants to know before the cards tell it.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ginstand.classing.color import BELOW_GRADE_RANK, CHART, ColorGrade, ColorGroup
from ginstand.errors import ValidationError

MIN_RD = Decimal("40.0")
MAX_RD = Decimal("90.0")
MIN_PLUS_B = Decimal("4.0")
MAX_PLUS_B = Decimal("20.0")

_PLACES = Decimal("0.1")

GROUP_BANDS: tuple[tuple[Decimal, ColorGroup], ...] = (
    (Decimal("9.0"), ColorGroup.WHITE),
    (Decimal("11.0"), ColorGroup.LIGHT_SPOTTED),
    (Decimal("13.0"), ColorGroup.SPOTTED),
    (Decimal("15.0"), ColorGroup.TINGED),
)
"""Upper bound of plus b for each group. Anything above the last is yellow stained."""

RANK_FLOORS: tuple[tuple[Decimal, int], ...] = (
    (Decimal("78.0"), 1),
    (Decimal("74.0"), 2),
    (Decimal("70.0"), 3),
    (Decimal("65.0"), 4),
    (Decimal("60.0"), 5),
    (Decimal("55.0"), 6),
    (Decimal("50.0"), 7),
)
"""Lowest Rd that still reaches each rank, best rank first.

One ladder for every column. Reflectance means the same thing whatever the
yellowness is, so the row does not move between columns. What moves is which
rows exist: the yellow columns are short at the top, and a reading that would be
rank 1 in white falls to the best rank its own column carries."""


@dataclass(frozen=True, slots=True)
class Reading:
    """One colorimeter reading off a sample."""

    rd: Decimal
    plus_b: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "rd", _bounded(self.rd, "Rd", MIN_RD, MAX_RD))
        object.__setattr__(self, "plus_b", _bounded(self.plus_b, "plus b", MIN_PLUS_B, MAX_PLUS_B))

    @property
    def group(self) -> ColorGroup:
        """Which column of the chart this reading falls in."""
        for bound, group in GROUP_BANDS:
            if self.plus_b <= bound:
                return group
        return ColorGroup.YELLOW_STAINED

    @property
    def rank(self) -> int:
        """The row of the ladder this reading reaches, before the column is applied."""
        for floor, rank in RANK_FLOORS:
            if self.rd >= floor:
                return rank
        return BELOW_GRADE_RANK

    @property
    def grade(self) -> ColorGrade:
        """The square of the chart this reading lands on."""
        group = self.group
        available = CHART[group]
        for rank in range(self.rank, BELOW_GRADE_RANK + 1):
            if rank in available:
                return ColorGrade(rank * 10 + group)
        return ColorGrade(BELOW_GRADE_RANK * 10 + group)


def _bounded(value: Decimal | str | int, name: str, low: Decimal, high: Decimal) -> Decimal:
    reading = Decimal(value).quantize(_PLACES, rounding=ROUND_HALF_UP)
    if reading < low or reading > high:
        raise ValidationError(name, f"must be between {low} and {high}, got {reading}")
    return reading


def estimate(rd: Decimal | str | int, plus_b: Decimal | str | int) -> ColorGrade:
    """The colour grade this gin would put on a sample reading this way."""
    return Reading(rd=Decimal(rd), plus_b=Decimal(plus_b)).grade


def agrees_with(reading: Reading, carded: ColorGrade) -> bool:
    """Whether the gin's estimate landed on the same square as the card."""
    return reading.grade == carded


def drift(reading: Reading, carded: ColorGrade) -> int:
    """How many ranks the estimate was off by, positive when the gin was optimistic.

    Only meaningful when both landed in the same group. A disagreement across
    groups is not a drift, it is a different reading, and it comes back as zero
    so that a report averaging drift is not quietly averaging in nonsense.
    """
    if reading.grade.group is not carded.group:
        return 0
    return carded.rank - reading.grade.rank
