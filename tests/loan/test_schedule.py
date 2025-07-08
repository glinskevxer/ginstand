"""The tables, and the one that is keyed on something other than its own reading."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ginstand.classing.color import CHART, ColorGrade, ColorGroup, valid_codes
from ginstand.errors import ScheduleError
from ginstand.loan.schedule import (
    COLOUR_POINTS,
    LEAF_POINTS,
    SPOTTED_STAPLE,
    WHITE_STAPLE,
    schedule_for,
)

SCHEDULE = schedule_for(2025)


def test_the_base_rate_is_cents_per_pound() -> None:
    assert SCHEDULE.base_rate == Decimal("52.0000")
    assert schedule_for(2026).base_rate == Decimal("52.5000")


def test_a_crop_year_that_is_not_loaded_names_the_ones_that_are() -> None:
    with pytest.raises(ScheduleError, match="the ones loaded are 2025, 2026"):
        schedule_for(2019)


def test_middling_white_is_the_base_of_the_colour_table() -> None:
    assert SCHEDULE.colour_points(ColorGrade(31)) == Decimal("0")


def test_better_colour_is_a_premium_and_worse_is_a_discount() -> None:
    assert SCHEDULE.colour_points(ColorGrade(11)) > 0
    assert SCHEDULE.colour_points(ColorGrade(51)) < 0
    assert SCHEDULE.colour_points(ColorGrade(54)) < SCHEDULE.colour_points(ColorGrade(51))


def test_the_colour_table_gets_worse_down_every_column() -> None:
    for group, ranks in CHART.items():
        priced = [rank for rank in ranks if rank != 8]
        points = [SCHEDULE.colour_points(ColorGrade(rank * 10 + group)) for rank in priced]
        assert points == sorted(points, reverse=True)


def test_every_priced_square_on_the_chart_has_a_row() -> None:
    for code in valid_codes():
        grade = ColorGrade(code)
        if grade.below_grade:
            continue
        assert code in COLOUR_POINTS
    assert len(COLOUR_POINTS) == len([c for c in valid_codes() if c // 10 != 8])


def test_a_below_grade_colour_has_no_value_rather_than_a_big_discount() -> None:
    with pytest.raises(ScheduleError, match="below grade and has no loan value"):
        SCHEDULE.colour_points(ColorGrade(81))


def test_leaf_three_is_the_base_of_the_leaf_table() -> None:
    assert SCHEDULE.leaf_points(3) == Decimal("0")
    assert SCHEDULE.leaf_points(1) > 0
    assert SCHEDULE.leaf_points(7) < 0


def test_the_leaf_table_gets_worse_all_the_way_down() -> None:
    points = [LEAF_POINTS[leaf] for leaf in range(1, 8)]
    assert points == sorted(points, reverse=True)


def test_leaf_eight_has_no_value_rather_than_a_big_discount() -> None:
    with pytest.raises(ScheduleError, match="below grade and has no loan value"):
        SCHEDULE.leaf_points(8)


def test_the_staple_premium_is_decided_by_the_colour_group() -> None:
    white = SCHEDULE.staple_points(ColorGrade(31), 37)
    tinged = SCHEDULE.staple_points(ColorGrade(34), 37)
    assert white == Decimal("330")
    assert tinged == Decimal("225")
    assert white > tinged


def test_light_spotted_stays_on_the_white_staple_ladder() -> None:
    assert SCHEDULE.staple_ladder(ColorGrade(32)) is WHITE_STAPLE
    assert SCHEDULE.staple_ladder(ColorGrade(33)) is SPOTTED_STAPLE


@pytest.mark.parametrize("group", list(ColorGroup))
def test_thirty_four_staple_is_the_base_on_every_ladder(group: ColorGroup) -> None:
    rank = next(r for r in CHART[group] if r != 8)
    assert SCHEDULE.staple_points(ColorGrade(rank * 10 + group), 34) == Decimal("0")


def test_a_bale_that_drops_a_group_loses_on_both_lines() -> None:
    better = SCHEDULE.colour_points(ColorGrade(32)) + SCHEDULE.staple_points(ColorGrade(32), 38)
    worse = SCHEDULE.colour_points(ColorGrade(33)) + SCHEDULE.staple_points(ColorGrade(33), 38)
    assert worse < better
    assert SCHEDULE.colour_points(ColorGrade(33)) < SCHEDULE.colour_points(ColorGrade(32))
    assert SCHEDULE.staple_points(ColorGrade(33), 38) < SCHEDULE.staple_points(ColorGrade(32), 38)


def test_the_micronaire_table_is_not_monotonic() -> None:
    assert SCHEDULE.micronaire_points(Decimal("4.0")) > 0
    assert SCHEDULE.micronaire_points(Decimal("3.2")) < 0
    assert SCHEDULE.micronaire_points(Decimal("5.5")) < 0
    assert SCHEDULE.micronaire_points(Decimal("4.6")) == Decimal("0")


def test_the_micronaire_premium_band_sits_in_the_middle() -> None:
    assert SCHEDULE.micronaire_points(Decimal("3.7")) == Decimal("125")
    assert SCHEDULE.micronaire_points(Decimal("4.2")) == Decimal("125")
    assert SCHEDULE.micronaire_points(Decimal("4.3")) == Decimal("0")
    assert SCHEDULE.micronaire_points(Decimal("3.6")) == Decimal("-35")


def test_the_low_side_of_the_mic_table_is_the_steeper_one() -> None:
    assert SCHEDULE.micronaire_points(Decimal("2.5")) < SCHEDULE.micronaire_points(Decimal("6.0"))


def test_the_strength_and_uniformity_tables_run_the_right_way() -> None:
    assert SCHEDULE.strength_points(Decimal("32.0")) == Decimal("100")
    assert SCHEDULE.strength_points(Decimal("27.0")) == Decimal("0")
    assert SCHEDULE.strength_points(Decimal("20.0")) == Decimal("-100")
    assert SCHEDULE.uniformity_points(Decimal("85.0")) == Decimal("90")
    assert SCHEDULE.uniformity_points(Decimal("81.0")) == Decimal("0")
    assert SCHEDULE.uniformity_points(Decimal("70.0")) == Decimal("-85")


def test_every_reading_a_card_can_carry_is_covered_by_its_ladder() -> None:
    for tenth in range(20, 71):
        SCHEDULE.micronaire_points(Decimal(tenth) / 10)
    for tenth in range(150, 451):
        SCHEDULE.strength_points(Decimal(tenth) / 10)
    for tenth in range(650, 951):
        SCHEDULE.uniformity_points(Decimal(tenth) / 10)
    for staple in range(24, 49):
        SCHEDULE.staple_points(ColorGrade(31), staple)
        SCHEDULE.staple_points(ColorGrade(33), staple)
