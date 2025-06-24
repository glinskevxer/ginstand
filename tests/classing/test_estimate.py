"""Plus b picks the column, Rd picks the row, and the estimate prices nothing."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ginstand.classing.color import ColorGrade, ColorGroup
from ginstand.classing.estimate import Reading, agrees_with, drift, estimate
from ginstand.errors import ValidationError


@pytest.mark.parametrize(
    ("plus_b", "group"),
    [
        ("7.0", ColorGroup.WHITE),
        ("9.0", ColorGroup.WHITE),
        ("9.1", ColorGroup.LIGHT_SPOTTED),
        ("11.0", ColorGroup.LIGHT_SPOTTED),
        ("12.0", ColorGroup.SPOTTED),
        ("14.0", ColorGroup.TINGED),
        ("15.1", ColorGroup.YELLOW_STAINED),
        ("19.0", ColorGroup.YELLOW_STAINED),
    ],
)
def test_yellowness_picks_the_column(plus_b: str, group: ColorGroup) -> None:
    assert Reading(rd=Decimal("75.0"), plus_b=Decimal(plus_b)).group is group


@pytest.mark.parametrize(
    ("rd", "code"),
    [
        ("80.0", 11),
        ("78.0", 11),
        ("77.9", 21),
        ("74.0", 21),
        ("70.0", 31),
        ("65.0", 41),
        ("60.0", 51),
        ("55.0", 61),
        ("50.0", 71),
        ("49.9", 81),
    ],
)
def test_reflectance_picks_the_row_in_white(rd: str, code: int) -> None:
    assert estimate(rd, "8.0") == ColorGrade(code)


def test_the_row_holds_across_columns_and_only_the_column_changes() -> None:
    assert estimate("70.0", "8.0") == ColorGrade(31)
    assert estimate("70.0", "10.0") == ColorGrade(32)
    assert estimate("70.0", "12.0") == ColorGrade(33)
    assert estimate("70.0", "14.0") == ColorGrade(34)
    assert estimate("70.0", "17.0") == ColorGrade(35)


def test_a_reading_falls_to_the_best_rank_its_own_column_carries() -> None:
    assert estimate("80.0", "8.0") == ColorGrade(11)
    assert estimate("80.0", "14.0") == ColorGrade(24)
    assert estimate("80.0", "17.0") == ColorGrade(25)


def test_a_column_that_stops_early_falls_to_below_grade() -> None:
    assert estimate("54.0", "14.0") == ColorGrade(84)
    assert estimate("64.0", "17.0") == ColorGrade(85)
    assert estimate("54.0", "10.0") == ColorGrade(82)


def test_good_ordinary_exists_only_in_the_white_column() -> None:
    assert estimate("52.0", "8.0") == ColorGrade(71)
    assert estimate("52.0", "10.0") == ColorGrade(82)
    assert estimate("52.0", "12.0") == ColorGrade(83)


def test_the_last_rank_a_column_carries_is_still_reachable() -> None:
    assert estimate("56.0", "10.0") == ColorGrade(62)
    assert estimate("56.0", "12.0") == ColorGrade(63)
    assert estimate("62.0", "14.0") == ColorGrade(54)


def test_every_square_the_estimator_can_reach_is_on_the_chart() -> None:
    for rd in range(40, 91, 1):
        for plus_b in range(4, 21):
            grade = estimate(Decimal(rd), Decimal(plus_b))
            assert ColorGrade(grade.code) == grade


@pytest.mark.parametrize(
    ("rd", "plus_b", "name"),
    [
        ("39.9", "8.0", "Rd"),
        ("90.1", "8.0", "Rd"),
        ("75.0", "3.9", "plus b"),
        ("75.0", "20.1", "plus b"),
    ],
)
def test_a_reading_off_the_instrument_range_is_refused(rd: str, plus_b: str, name: str) -> None:
    with pytest.raises(ValidationError, match=name):
        estimate(rd, plus_b)


def test_a_reading_is_quantised_to_the_place_the_instrument_gives() -> None:
    reading = Reading(rd=Decimal("74.04"), plus_b=Decimal("8.04"))
    assert reading.rd == Decimal("74.0")
    assert reading.plus_b == Decimal("8.0")


def test_the_estimate_can_be_checked_against_the_card() -> None:
    reading = Reading(rd=Decimal("70.0"), plus_b=Decimal("8.0"))
    assert agrees_with(reading, ColorGrade(31))
    assert not agrees_with(reading, ColorGrade(41))


def test_drift_is_positive_when_the_gin_was_optimistic() -> None:
    reading = Reading(rd=Decimal("70.0"), plus_b=Decimal("8.0"))
    assert drift(reading, ColorGrade(41)) == 1
    assert drift(reading, ColorGrade(21)) == -1
    assert drift(reading, ColorGrade(31)) == 0


def test_a_disagreement_across_groups_is_not_a_drift() -> None:
    reading = Reading(rd=Decimal("70.0"), plus_b=Decimal("8.0"))
    assert drift(reading, ColorGrade(32)) == 0
