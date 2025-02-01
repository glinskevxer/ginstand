"""Whole units split in proportion, and the split always adds back to the whole."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ginstand.errors import ValidationError
from ginstand.units.apportion import apportion, largest_remainder_order, proportion


def test_an_even_split_needs_no_remainder() -> None:
    assert apportion(10, [1, 1]) == [5, 5]
    assert apportion(9, [2, 1]) == [6, 3]


def test_the_leftover_goes_to_the_largest_fraction_first() -> None:
    # 7 bales on 3 equal producers: 2 each, one over, and the first claims it.
    assert apportion(7, [1, 1, 1]) == [3, 2, 2]


def test_a_realistic_run_adds_back_to_the_bale_count() -> None:
    weights = [122_400, 88_150, 46_900, 15_320]
    shares = apportion(61, weights)
    assert sum(shares) == 61
    assert shares == [27, 20, 11, 3]


def test_a_producer_with_no_cotton_in_the_run_gets_nothing() -> None:
    assert apportion(10, [5, 0, 5]) == [5, 0, 5]


def test_splitting_nothing_gives_everyone_nothing() -> None:
    assert apportion(0, [3, 1]) == [0, 0]


def test_more_claimants_than_units_still_adds_back() -> None:
    shares = apportion(2, [10, 9, 8, 7, 6])
    assert sum(shares) == 2
    assert shares == [1, 1, 0, 0, 0]


@pytest.mark.parametrize(
    ("total", "weights"),
    [
        (61, [122_400, 88_150, 46_900, 15_320]),
        (7, [1, 1, 1]),
        (100, [33, 33, 34]),
        (13, [1, 2, 3, 4, 5]),
        (1, [1, 1, 1, 1]),
    ],
)
def test_the_split_never_loses_or_invents_a_unit(total: int, weights: list[int]) -> None:
    assert sum(apportion(total, weights)) == total


def test_a_negative_total_is_refused() -> None:
    with pytest.raises(ValidationError, match="must not be negative"):
        apportion(-1, [1])


def test_an_empty_claimant_list_is_refused() -> None:
    with pytest.raises(ValidationError, match="nobody to split between"):
        apportion(10, [])


def test_a_negative_weight_names_its_position() -> None:
    with pytest.raises(ValidationError, match=r"weights\[1\]"):
        apportion(10, [5, -1])


def test_weights_that_are_all_zero_have_nothing_to_split_on() -> None:
    with pytest.raises(ValidationError, match="all zero"):
        apportion(10, [0, 0])


def test_the_queue_for_the_odd_unit_can_be_printed() -> None:
    assert largest_remainder_order([1, 1, 1], 7) == [0, 1, 2]
    assert largest_remainder_order([122_400, 88_150, 46_900, 15_320], 61) == [1, 2, 3, 0]


def test_the_queue_refuses_the_same_inputs_the_split_does() -> None:
    with pytest.raises(ValidationError, match="nobody to split between"):
        largest_remainder_order([], 5)
    with pytest.raises(ValidationError, match="all zero"):
        largest_remainder_order([0, 0], 5)


def test_a_proportion_carries_four_places_by_default() -> None:
    assert proportion(7_450, 21_300) == Decimal("0.3498")
    assert proportion(1, 3) == Decimal("0.3333")


def test_a_proportion_can_be_asked_for_more_places() -> None:
    assert proportion(1, 3, places="0.000001") == Decimal("0.333333")


def test_a_run_with_no_seed_cotton_has_no_turnout_rather_than_a_bad_one() -> None:
    with pytest.raises(ValidationError, match="is zero"):
        proportion(0, 0)


def test_a_negative_proportion_is_refused() -> None:
    with pytest.raises(ValidationError, match="must not be negative"):
        proportion(-1, 10)
