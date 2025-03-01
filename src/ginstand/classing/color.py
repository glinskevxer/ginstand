"""Colour grade: the two digit code, and the colorimeter reading behind it.

The code is read as rank then group. 31 is rank 3, group 1, which is Middling
White. 44 is rank 4, group 4, which is Strict Low Middling Tinged. Rank 8 in any
group is below grade, and below grade is not a bad price, it is no price: those
bales come out of the loan schedule entirely.

Not every rank exists in every group. The chart is short at the bottom for the
yellow groups because cotton that yellow does not come in the better ranks.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from ginstand.errors import ValidationError

BELOW_GRADE_RANK = 8


class ColorGroup(IntEnum):
    """The second digit of the colour code."""

    WHITE = 1
    LIGHT_SPOTTED = 2
    SPOTTED = 3
    TINGED = 4
    YELLOW_STAINED = 5


GROUP_NAMES: dict[ColorGroup, str] = {
    ColorGroup.WHITE: "White",
    ColorGroup.LIGHT_SPOTTED: "Light Spotted",
    ColorGroup.SPOTTED: "Spotted",
    ColorGroup.TINGED: "Tinged",
    ColorGroup.YELLOW_STAINED: "Yellow Stained",
}

RANK_NAMES: dict[int, str] = {
    1: "Good Middling",
    2: "Strict Middling",
    3: "Middling",
    4: "Strict Low Middling",
    5: "Low Middling",
    6: "Strict Good Ordinary",
    7: "Good Ordinary",
    8: "Below Grade",
}

CHART: dict[ColorGroup, tuple[int, ...]] = {
    ColorGroup.WHITE: (1, 2, 3, 4, 5, 6, 7, 8),
    ColorGroup.LIGHT_SPOTTED: (1, 2, 3, 4, 5, 6, 8),
    ColorGroup.SPOTTED: (1, 2, 3, 4, 5, 6, 8),
    ColorGroup.TINGED: (2, 3, 4, 5, 8),
    ColorGroup.YELLOW_STAINED: (2, 3, 8),
}
"""Which ranks the chart carries in each group."""


def valid_codes() -> tuple[int, ...]:
    """Every colour code the chart allows, in ascending order."""
    return tuple(sorted(rank * 10 + group for group, ranks in CHART.items() for rank in ranks))


@dataclass(frozen=True, slots=True)
class ColorGrade:
    """One square of the colour chart."""

    code: int

    def __post_init__(self) -> None:
        if isinstance(self.code, bool) or not isinstance(self.code, int):
            raise ValidationError("colour grade", "must be a two digit code")
        if self.code not in valid_codes():
            raise ValidationError("colour grade", f"{self.code} is not a square on the chart")

    @property
    def rank(self) -> int:
        """The first digit. Lower is better."""
        return self.code // 10

    @property
    def group(self) -> ColorGroup:
        """The second digit."""
        return ColorGroup(self.code % 10)

    @property
    def below_grade(self) -> bool:
        """Whether this square is off the bottom of the schedule."""
        return self.rank == BELOW_GRADE_RANK

    @property
    def name(self) -> str:
        """How the card writes it out."""
        if self.below_grade:
            return f"Below Grade {GROUP_NAMES[self.group]}"
        return f"{RANK_NAMES[self.rank]} {GROUP_NAMES[self.group]}"

    def __str__(self) -> str:
        return f"{self.code}"
