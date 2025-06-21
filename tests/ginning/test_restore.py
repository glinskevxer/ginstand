"""Restoration is capped by the storage ceiling and by a fraction of the bale."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ginstand.errors import ValidationError
from ginstand.ginning.restore import (
    MAX_ADDED_FRACTION,
    cap_pounds,
    highest_allowed,
    plan,
)
from ginstand.units.moisture import SAFE_BALE_MOISTURE


def test_the_cap_is_a_fraction_of_the_pressed_weight() -> None:
    assert cap_pounds(500) == 10
    assert cap_pounds(600) == 12
    assert cap_pounds(490) == 9


def test_the_cap_rounds_down_so_it_is_never_generous() -> None:
    assert Decimal(490) * MAX_ADDED_FRACTION == Decimal("9.800")
    assert cap_pounds(490) == 9


def test_a_bale_with_no_weight_has_no_cap() -> None:
    with pytest.raises(ValidationError, match="must be above zero"):
        cap_pounds(0)


def test_a_plan_says_how_much_water_goes_in() -> None:
    step = plan(490, Decimal("5.0"), Decimal("7.0"))
    assert step.final_pounds == 501
    assert step.added_pounds == 11
    assert step.allowed_pounds == 9


def test_a_plan_inside_both_caps_is_allowed() -> None:
    step = plan(490, Decimal("5.5"), Decimal("7.0"))
    assert step.allowed
    assert step.refusal == ""


def test_going_past_the_storage_ceiling_is_refused_first() -> None:
    step = plan(490, Decimal("5.0"), Decimal("8.0"))
    assert not step.storable
    assert not step.allowed
    assert "above the storage ceiling" in step.refusal


def test_the_ceiling_itself_is_allowed_if_the_water_fits() -> None:
    step = plan(490, Decimal("7.0"), SAFE_BALE_MOISTURE)
    assert step.storable
    assert step.allowed


def test_too_much_water_is_refused_with_both_figures() -> None:
    step = plan(490, Decimal("5.0"), Decimal("7.4"))
    assert step.storable
    assert not step.within_cap
    assert "more than the 9 lb allowed on a 490 lb bale" in step.refusal


def test_drying_is_not_restoration_and_is_refused() -> None:
    with pytest.raises(ValidationError, match="which is drying"):
        plan(490, Decimal("7.0"), Decimal("6.0"))


def test_restoring_to_where_it_already_is_adds_nothing() -> None:
    step = plan(490, Decimal("6.8"), Decimal("6.8"))
    assert step.added_pounds == 0
    assert step.allowed


def test_the_cap_in_pounds_moves_with_the_bale() -> None:
    assert cap_pounds(400) == 8
    assert cap_pounds(600) == 12


def test_the_cap_in_points_does_not_move_with_the_bale() -> None:
    light = highest_allowed(400, Decimal("5.0"))
    heavy = highest_allowed(600, Decimal("5.0"))
    assert light == heavy


def test_the_highest_allowed_stops_at_the_storage_ceiling() -> None:
    assert highest_allowed(490, Decimal("7.4")) == SAFE_BALE_MOISTURE


def test_the_highest_allowed_stops_at_the_water_cap_when_that_bites_first() -> None:
    reached = highest_allowed(490, Decimal("5.0"))
    assert reached < SAFE_BALE_MOISTURE
    assert plan(490, Decimal("5.0"), reached).allowed
    assert not plan(490, Decimal("5.0"), reached + Decimal("0.1")).allowed


def test_a_bale_already_at_the_ceiling_can_go_no_further() -> None:
    assert highest_allowed(490, SAFE_BALE_MOISTURE) == SAFE_BALE_MOISTURE


def test_a_moisture_off_the_meter_range_is_refused() -> None:
    with pytest.raises(ValidationError, match="no more than 25.0%"):
        plan(490, Decimal("5.0"), Decimal("30.0"))
