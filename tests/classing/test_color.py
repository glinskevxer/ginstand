"""The colour chart is a fixed set of squares, and rank 8 is off the schedule."""

from __future__ import annotations

import pytest

from ginstand.classing.color import (
    BELOW_GRADE_RANK,
    CHART,
    ColorGrade,
    ColorGroup,
    valid_codes,
)
from ginstand.errors import ValidationError


def test_a_code_reads_as_rank_then_group() -> None:
    grade = ColorGrade(31)
    assert grade.rank == 3
    assert grade.group is ColorGroup.WHITE
    assert grade.name == "Middling White"


def test_the_second_digit_picks_the_group() -> None:
    assert ColorGrade(44).group is ColorGroup.TINGED
    assert ColorGrade(44).name == "Strict Low Middling Tinged"
    assert ColorGrade(35).group is ColorGroup.YELLOW_STAINED
    assert ColorGrade(35).name == "Middling Yellow Stained"


def test_rank_eight_is_below_grade_in_every_group_that_has_it() -> None:
    for group in ColorGroup:
        code = BELOW_GRADE_RANK * 10 + group
        grade = ColorGrade(code)
        assert grade.below_grade
        assert grade.name.startswith("Below Grade")


def test_a_square_that_is_not_on_the_chart_is_refused() -> None:
    with pytest.raises(ValidationError, match="is not a square on the chart"):
        ColorGrade(14)


def test_the_yellow_groups_are_short_at_the_top() -> None:
    assert 1 not in CHART[ColorGroup.TINGED]
    assert 1 not in CHART[ColorGroup.YELLOW_STAINED]
    with pytest.raises(ValidationError):
        ColorGrade(15)
    with pytest.raises(ValidationError):
        ColorGrade(45)


def test_good_ordinary_exists_only_in_white() -> None:
    assert ColorGrade(71).name == "Good Ordinary White"
    for group in (ColorGroup.LIGHT_SPOTTED, ColorGroup.SPOTTED):
        with pytest.raises(ValidationError):
            ColorGrade(70 + group)


@pytest.mark.parametrize("code", [0, 9, 10, 91, 100, -31])
def test_a_code_outside_the_two_digit_shape_is_refused(code: int) -> None:
    with pytest.raises(ValidationError):
        ColorGrade(code)


def test_a_bool_is_not_a_colour_code() -> None:
    with pytest.raises(ValidationError, match="two digit code"):
        ColorGrade(True)


def test_every_code_on_the_chart_builds() -> None:
    codes = valid_codes()
    assert len(codes) == sum(len(ranks) for ranks in CHART.values())
    assert codes == tuple(sorted(codes))
    for code in codes:
        assert ColorGrade(code).code == code


def test_the_white_column_runs_the_whole_way_down() -> None:
    assert CHART[ColorGroup.WHITE] == (1, 2, 3, 4, 5, 6, 7, 8)


def test_a_grade_prints_as_its_code() -> None:
    assert str(ColorGrade(31)) == "31"


def test_a_grade_is_hashable_so_it_can_key_a_schedule() -> None:
    assert len({ColorGrade(31), ColorGrade(31), ColorGrade(41)}) == 2
