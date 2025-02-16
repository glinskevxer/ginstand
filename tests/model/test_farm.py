"""Farms and fields, and the per acre figures a producer checks first."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ginstand.errors import ValidationError
from ginstand.model.farm import MAX_FIELD_ACRES, Farm, Field


def test_a_farm_normalises_every_reference_on_it() -> None:
    farm = Farm(ref=" f-3 ", producer=" p-12 ", name="  Home Place  ", fsa_number=" t4471 ")
    assert (farm.ref, farm.producer, farm.name, farm.fsa_number) == (
        "F-3",
        "P-12",
        "Home Place",
        "T4471",
    )


def test_a_farm_without_a_name_is_refused() -> None:
    with pytest.raises(ValidationError, match="farm name: is empty"):
        Farm(ref="F-3", producer="P-12", name="  ")


def test_a_field_carries_its_farm_its_lease_and_its_acres() -> None:
    plot = Field(ref="fl-9", farm="f-3", name="North 80", acres=Decimal("78.4"), lease="l-2")
    assert (plot.ref, plot.farm, plot.lease) == ("FL-9", "F-3", "L-2")
    assert plot.acres == Decimal("78.40")
    assert not plot.irrigated


def test_acres_are_held_to_two_places() -> None:
    plot = Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("78.4449"), lease="L-2")
    assert plot.acres == Decimal("78.44")


@pytest.mark.parametrize("acres", [Decimal("0"), Decimal("-1"), Decimal("0.001")])
def test_a_field_with_no_acres_in_it_is_refused(acres: Decimal) -> None:
    with pytest.raises(ValidationError, match="must be above zero"):
        Field(ref="FL-9", farm="F-3", name="North 80", acres=acres, lease="L-2")


def test_a_field_the_size_of_a_county_is_a_typing_mistake() -> None:
    with pytest.raises(ValidationError, match="no more than 5000"):
        Field(
            ref="FL-9",
            farm="F-3",
            name="North 80",
            acres=MAX_FIELD_ACRES + 1,
            lease="L-2",
        )


def test_a_field_without_a_name_is_refused() -> None:
    with pytest.raises(ValidationError, match="field name: is empty"):
        Field(ref="FL-9", farm="F-3", name="", acres=Decimal("40"), lease="L-2")


def test_bales_per_acre_carries_two_places() -> None:
    plot = Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("78.40"), lease="L-2")
    assert plot.yield_per_acre(112) == Decimal("1.43")
    assert plot.yield_per_acre(0) == Decimal("0.00")


def test_lint_per_acre_carries_one_place() -> None:
    plot = Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("78.40"), lease="L-2")
    assert plot.lint_per_acre(56_000) == Decimal("714.3")


def test_a_negative_yield_is_refused_rather_than_printed() -> None:
    plot = Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("78.40"), lease="L-2")
    with pytest.raises(ValidationError, match="must not be negative"):
        plot.yield_per_acre(-1)
    with pytest.raises(ValidationError, match="must not be negative"):
        plot.lint_per_acre(-1)


def test_a_field_is_frozen() -> None:
    plot = Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("78.40"), lease="L-2")
    with pytest.raises(AttributeError):
        plot.acres = Decimal("100")  # type: ignore[misc]
