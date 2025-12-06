"""The published premium and discount tables, one set per crop year.

The office publishes a single combined table. This gin stores it as its parts,
because the parts move independently between years and a diff of two crop years
is unreadable when it is one flat table of two thousand rows.

Below grade codes are deliberately absent from the colour table. Looking one up
raises rather than returning a large discount, because a below grade bale has no
loan value at all and a number would invite somebody to use it.

The staple table is kept per colour family, and that is the part of the schedule
worth understanding. A bale's staple premium is not a property of its staple. A
thirty seven staple is worth three hundred and thirty points on white and two
hundred and twenty five on tinged, so a bale that classes a group worse loses
twice: once on the colour line and again on the staple line.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ginstand.errors import ScheduleError
from ginstand.grades.color import ColorGrade, ColorGroup
from ginstand.grades.matter import BELOW_GRADE_LEAF
from ginstand.loan.points import Band, Ladder, Points

WHITE_FAMILY = (ColorGroup.WHITE, ColorGroup.LIGHT_SPOTTED)
"""The colour groups that carry the better staple ladder."""

COLOUR_POINTS: dict[int, Points] = {
    11: Decimal("130"),
    21: Decimal("75"),
    31: Decimal("0"),
    41: Decimal("-95"),
    51: Decimal("-260"),
    61: Decimal("-510"),
    71: Decimal("-760"),
    12: Decimal("55"),
    22: Decimal("15"),
    32: Decimal("-60"),
    42: Decimal("-185"),
    52: Decimal("-370"),
    62: Decimal("-640"),
    13: Decimal("-25"),
    23: Decimal("-70"),
    33: Decimal("-175"),
    43: Decimal("-330"),
    53: Decimal("-545"),
    63: Decimal("-830"),
    24: Decimal("-395"),
    34: Decimal("-540"),
    44: Decimal("-720"),
    54: Decimal("-940"),
    25: Decimal("-690"),
    35: Decimal("-880"),
}

LEAF_POINTS: dict[int, Points] = {
    1: Decimal("25"),
    2: Decimal("10"),
    3: Decimal("0"),
    4: Decimal("-35"),
    5: Decimal("-95"),
    6: Decimal("-190"),
    7: Decimal("-320"),
}


def _staple_ladder(name: str, rungs: tuple[tuple[str, str, str], ...]) -> Ladder:
    return Ladder(
        name, [Band(Decimal(low), Decimal(high), Decimal(pts)) for low, high, pts in rungs]
    )


WHITE_STAPLE = _staple_ladder(
    "staple on white and light spotted",
    (
        ("24", "32", "-450"),
        ("32", "34", "-180"),
        ("34", "35", "0"),
        ("35", "36", "130"),
        ("36", "37", "245"),
        ("37", "38", "330"),
        ("38", "49", "385"),
    ),
)

SPOTTED_STAPLE = _staple_ladder(
    "staple on spotted and worse",
    (
        ("24", "32", "-560"),
        ("32", "34", "-250"),
        ("34", "35", "0"),
        ("35", "36", "95"),
        ("36", "37", "170"),
        ("37", "38", "225"),
        ("38", "49", "260"),
    ),
)

MICRONAIRE = Ladder(
    "micronaire",
    [
        Band(Decimal("2.0"), Decimal("2.7"), Decimal("-580"), "very fine"),
        Band(Decimal("2.7"), Decimal("3.0"), Decimal("-455"), "fine"),
        Band(Decimal("3.0"), Decimal("3.3"), Decimal("-280"), "low"),
        Band(Decimal("3.3"), Decimal("3.5"), Decimal("-110"), "slightly low"),
        Band(Decimal("3.5"), Decimal("3.7"), Decimal("-35"), "base low"),
        Band(Decimal("3.7"), Decimal("4.3"), Decimal("125"), "premium range"),
        Band(Decimal("4.3"), Decimal("5.0"), Decimal("0"), "base high"),
        Band(Decimal("5.0"), Decimal("5.3"), Decimal("-125"), "coarse"),
        Band(Decimal("5.3"), Decimal("7.1"), Decimal("-320"), "very coarse"),
    ],
)

STRENGTH = Ladder(
    "strength",
    [
        Band(Decimal("15.0"), Decimal("24.0"), Decimal("-100")),
        Band(Decimal("24.0"), Decimal("26.0"), Decimal("-50")),
        Band(Decimal("26.0"), Decimal("29.0"), Decimal("0")),
        Band(Decimal("29.0"), Decimal("31.0"), Decimal("50")),
        Band(Decimal("31.0"), Decimal("45.1"), Decimal("100")),
    ],
)

UNIFORMITY = Ladder(
    "uniformity",
    [
        Band(Decimal("65.0"), Decimal("78.0"), Decimal("-85")),
        Band(Decimal("78.0"), Decimal("80.0"), Decimal("-40")),
        Band(Decimal("80.0"), Decimal("82.0"), Decimal("0")),
        Band(Decimal("82.0"), Decimal("84.0"), Decimal("45")),
        Band(Decimal("84.0"), Decimal("95.1"), Decimal("90")),
    ],
)


@dataclass(frozen=True, slots=True)
class Schedule:
    """One crop year's loan schedule."""

    crop_year: int
    base_rate: Decimal
    """Cents per pound before any premium or discount."""

    def colour_points(self, grade: ColorGrade) -> Points:
        """Points off the colour table."""
        if grade.below_grade:
            raise ScheduleError(f"colour grade {grade.code} is below grade and has no loan value")
        try:
            return COLOUR_POINTS[grade.code]
        except KeyError:
            raise ScheduleError(
                f"the {self.crop_year} colour table has no row for {grade.code}"
            ) from None

    def leaf_points(self, leaf: int) -> Points:
        """Points off the leaf table."""
        if leaf == BELOW_GRADE_LEAF:
            raise ScheduleError("leaf grade 8 is below grade and has no loan value")
        try:
            return LEAF_POINTS[leaf]
        except KeyError:
            raise ScheduleError(
                f"the {self.crop_year} leaf table has no row for leaf {leaf}"
            ) from None

    def staple_ladder(self, grade: ColorGrade) -> Ladder:
        """Which staple ladder this bale's colour puts it on."""
        return WHITE_STAPLE if grade.group in WHITE_FAMILY else SPOTTED_STAPLE

    def staple_points(self, grade: ColorGrade, staple: int) -> Points:
        """Points off the staple table, which the colour group decides."""
        return self.staple_ladder(grade).points_for(Decimal(staple))

    def micronaire_points(self, micronaire: Decimal) -> Points:
        """Points off the micronaire table."""
        return MICRONAIRE.points_for(micronaire)

    def strength_points(self, strength: Decimal) -> Points:
        """Points off the strength table."""
        return STRENGTH.points_for(strength)

    def uniformity_points(self, uniformity: Decimal) -> Points:
        """Points off the uniformity table."""
        return UNIFORMITY.points_for(uniformity)


SCHEDULES: dict[int, Schedule] = {
    2025: Schedule(crop_year=2025, base_rate=Decimal("52.0000")),
    2026: Schedule(crop_year=2026, base_rate=Decimal("52.5000")),
}


def schedule_for(crop_year: int) -> Schedule:
    """The schedule for a crop year. Raises if that year is not loaded."""
    try:
        return SCHEDULES[crop_year]
    except KeyError:
        raise ScheduleError(
            f"no loan schedule is loaded for crop year {crop_year}, "
            f"the ones loaded are {', '.join(str(y) for y in sorted(SCHEDULES))}"
        ) from None
