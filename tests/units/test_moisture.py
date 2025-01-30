"""Moisture is wet basis to one place, and dry weight is what carries across it."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ginstand.errors import ValidationError
from ginstand.units.moisture import (
    DRY_GINNING_FLOOR,
    DRYER_THRESHOLD,
    SAFE_BALE_MOISTURE,
    dry_weight,
    format_moisture,
    moisture,
    needs_drying,
    reweigh,
    safe_to_store,
    too_dry_to_gin,
    water_added,
    weight_at,
)


def test_a_reading_is_quantised_to_the_one_place_the_meter_gives() -> None:
    assert moisture("7.45") == Decimal("7.5")
    assert moisture("7.44") == Decimal("7.4")
    assert moisture(7) == Decimal("7.0")


def test_a_negative_reading_is_a_fault() -> None:
    with pytest.raises(ValidationError, match="must not be negative"):
        moisture("-0.1")


def test_a_reading_past_the_meter_range_is_refused() -> None:
    with pytest.raises(ValidationError, match="no more than 25.0%"):
        moisture("25.1")


def test_a_non_number_reading_is_refused() -> None:
    with pytest.raises(ValidationError, match="is not a number"):
        moisture("damp")


def test_dry_weight_is_the_matter_left_after_the_water() -> None:
    assert dry_weight(1000, Decimal("10.0")) == 900
    assert dry_weight(500, Decimal("7.5")) == 463
    assert dry_weight(0, Decimal("7.5")) == 0


def test_dry_weight_of_bone_dry_cotton_is_its_own_weight() -> None:
    assert dry_weight(500, Decimal("0.0")) == 500


def test_a_negative_weight_has_no_dry_weight() -> None:
    with pytest.raises(ValidationError, match="must not be negative"):
        dry_weight(-1, Decimal("7.0"))


def test_dry_matter_weighs_more_once_it_holds_moisture() -> None:
    assert weight_at(900, Decimal("10.0")) == 1000
    assert weight_at(463, Decimal("7.5")) == 501


def test_the_round_trip_lands_within_a_pound() -> None:
    for pounds in (480, 500, 512, 1_000, 22_060):
        dry = dry_weight(pounds, Decimal("11.0"))
        assert abs(weight_at(dry, Decimal("11.0")) - pounds) <= 1


def test_reweighing_moves_the_weight_with_the_moisture() -> None:
    assert reweigh(1000, Decimal("12.0"), Decimal("7.0")) == 946
    assert reweigh(1000, Decimal("7.0"), Decimal("12.0")) == 1057


def test_reweighing_at_the_same_moisture_changes_nothing() -> None:
    assert reweigh(22_060, Decimal("9.4"), Decimal("9.4")) == 22_060


def test_water_added_is_negative_when_the_module_dried_in_the_yard() -> None:
    assert water_added(22_060, Decimal("12.0"), Decimal("9.0")) < 0
    assert water_added(500, Decimal("5.0"), Decimal("7.0")) > 0
    assert water_added(500, Decimal("7.0"), Decimal("7.0")) == 0


def test_the_storage_ceiling_is_inclusive() -> None:
    assert safe_to_store(SAFE_BALE_MOISTURE)
    assert safe_to_store(Decimal("7.4"))
    assert not safe_to_store(Decimal("7.6"))


def test_the_dryer_threshold_is_exclusive() -> None:
    assert not needs_drying(DRYER_THRESHOLD)
    assert needs_drying(Decimal("8.1"))
    assert not needs_drying(Decimal("6.0"))


def test_the_ginning_floor_is_exclusive() -> None:
    assert not too_dry_to_gin(DRY_GINNING_FLOOR)
    assert too_dry_to_gin(Decimal("4.9"))


def test_a_ticket_prints_the_reading_with_its_sign() -> None:
    assert format_moisture(Decimal("7.5")) == "7.5%"
    assert format_moisture("11") == "11.0%"
