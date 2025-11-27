"""The published rates, and that every year has a complete set."""

from __future__ import annotations

import pytest

from ginstand.charges.published import (
    SEED_PRICES,
    STORAGE,
    TARIFFS,
    published_years,
    seed_price_for,
    storage_for,
    tariff_for,
)
from ginstand.errors import ScheduleError
from ginstand.loan.schedule import SCHEDULES
from ginstand.units.money import money


def test_the_published_years_have_a_full_set_of_rates() -> None:
    assert published_years() == (2025, 2026)
    for year in published_years():
        assert year in TARIFFS
        assert year in SEED_PRICES
        assert year in STORAGE


def test_every_published_year_also_has_a_loan_schedule() -> None:
    for year in published_years():
        assert year in SCHEDULES


def test_a_year_with_no_rates_names_the_ones_there_are() -> None:
    with pytest.raises(ScheduleError, match="the ones published are 2025, 2026"):
        tariff_for(2019)
    with pytest.raises(ScheduleError, match="seed price"):
        seed_price_for(2019)
    with pytest.raises(ScheduleError, match="storage contract"):
        storage_for(2019)


def test_the_ginning_rate_is_charged_on_hundredweight() -> None:
    line = tariff_for(2025).line("GIN")
    assert line.rate == money("3.75")
    assert "cwt" in str(line.basis)


def test_the_rates_moved_between_the_two_years() -> None:
    assert tariff_for(2026).line("GIN").rate > tariff_for(2025).line("GIN").rate
    assert seed_price_for(2026) > seed_price_for(2025)
    assert storage_for(2026).per_day > storage_for(2025).per_day


def test_every_tariff_carries_the_same_codes() -> None:
    assert set(tariff_for(2025).codes) == set(tariff_for(2026).codes)


def test_the_optional_lines_are_the_ones_that_are_asked_for() -> None:
    optional = {line.code for line in tariff_for(2025).lines if line.optional}
    assert optional == {"REST", "PICK"}


def test_the_storage_contract_has_a_free_period_inside_its_minimum() -> None:
    for year in published_years():
        contract = storage_for(year)
        assert contract.free_days < contract.minimum_days
