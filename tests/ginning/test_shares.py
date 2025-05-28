"""The carry decides the allocation, and the allocation decides the next carry."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ginstand.errors import ValidationError
from ginstand.ginning.shares import carries_from, split_bales


def test_an_even_split_needs_no_carry() -> None:
    split = split_bales(10, {"P-1": 5_000, "P-2": 5_000})
    assert [share.bales for share in split.shares] == [5, 5]
    assert carries_from(split) == {"P-1": Decimal("0"), "P-2": Decimal("0")}


def test_the_bales_always_add_back_to_the_run() -> None:
    split = split_bales(61, {"P-1": 122_400, "P-2": 88_150, "P-3": 46_900, "P-4": 15_320})
    assert sum(share.bales for share in split.shares) == 61


def test_the_carry_is_what_the_producer_was_owed_and_did_not_get() -> None:
    split = split_bales(3, {"P-1": 2_000, "P-2": 1_000})
    first = split.for_producer("P-1")
    assert first.entitlement == Decimal("2.000000")
    assert first.bales == 2
    assert first.carried_out == Decimal("0.000000")
    second = split.for_producer("P-2")
    assert second.bales == 1


def test_a_fraction_owed_is_carried_rather_than_rounded_away() -> None:
    split = split_bales(10, {"P-1": 3_000, "P-2": 7_000})
    assert split.for_producer("P-1").bales == 3
    assert split.for_producer("P-2").bales == 7
    split = split_bales(10, {"P-1": 3_500, "P-2": 6_500})
    assert split.for_producer("P-1").carried_out == Decimal("-0.500000")
    assert split.for_producer("P-2").carried_out == Decimal("0.500000")


def test_a_carry_brought_in_can_win_a_producer_a_whole_bale() -> None:
    without = split_bales(3, {"P-1": 1_600, "P-2": 1_400})
    assert without.for_producer("P-1").bales == 2
    with_carry = split_bales(3, {"P-1": 1_600, "P-2": 1_400}, {"P-2": Decimal("0.6")})
    assert with_carry.for_producer("P-2").bales == 2
    assert with_carry.for_producer("P-1").bales == 1


def test_the_carry_out_accounts_for_the_carry_in() -> None:
    split = split_bales(3, {"P-1": 1_600, "P-2": 1_400}, {"P-2": Decimal("0.6")})
    second = split.for_producer("P-2")
    assert second.carried_in == Decimal("0.6")
    assert second.claim == second.entitlement + Decimal("0.6")
    assert second.carried_out == second.claim - 2


def test_two_runs_in_a_row_settle_the_fraction() -> None:
    first = split_bales(1, {"P-1": 500, "P-2": 500})
    assert [s.bales for s in first.shares] == [1, 0]
    second = split_bales(1, {"P-1": 500, "P-2": 500}, carries_from(first))
    assert second.for_producer("P-2").bales == 1
    assert second.for_producer("P-1").bales == 0


def test_the_order_given_decides_who_gets_the_odd_bale() -> None:
    forwards = split_bales(1, {"P-1": 500, "P-2": 500})
    backwards = split_bales(1, {"P-2": 500, "P-1": 500})
    assert forwards.for_producer("P-1").bales == 1
    assert backwards.for_producer("P-2").bales == 1


def test_a_producer_with_no_cotton_in_the_run_gets_nothing() -> None:
    split = split_bales(10, {"P-1": 5_000, "P-2": 0})
    assert split.for_producer("P-2").bales == 0
    assert split.for_producer("P-1").bales == 10


def test_a_run_with_no_bales_yet_still_records_the_claims() -> None:
    split = split_bales(0, {"P-1": 5_000, "P-2": 5_000})
    assert [share.bales for share in split.shares] == [0, 0]
    assert split.seed_cotton_pounds == 10_000


def test_asking_about_a_producer_who_was_not_in_the_run_is_refused() -> None:
    split = split_bales(10, {"P-1": 5_000})
    with pytest.raises(ValidationError, match="put no cotton into this run"):
        split.for_producer("P-9")


def test_the_producers_read_back_in_the_order_given() -> None:
    split = split_bales(10, {"P-3": 1, "P-1": 2, "P-2": 3})
    assert split.producers == ("P-3", "P-1", "P-2")


@pytest.mark.parametrize(
    ("bales", "weights", "message"),
    [
        (-1, {"P-1": 100}, "must not be negative"),
        (10, {}, "no producer put cotton"),
        (10, {"P-1": 0}, "no seed cotton in it"),
    ],
)
def test_a_split_that_cannot_be_made_is_refused(
    bales: int, weights: dict[str, int], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        split_bales(bales, weights)


def test_a_negative_weight_names_the_producer() -> None:
    with pytest.raises(ValidationError, match="^P-2:"):
        split_bales(10, {"P-1": 500, "P-2": -1})


def test_the_allocation_line_shows_the_arithmetic() -> None:
    split = split_bales(3, {"P-1": 1_600, "P-2": 1_400})
    assert split.for_producer("P-1").line.startswith("P-1  1,600 lb  claim 1.600000  2 bales")
