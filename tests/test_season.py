"""The crop year runs August to July, and no code here reads the wall clock."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from ginstand.errors import ValidationError
from ginstand.season import (
    check_crop_year,
    crop_year_bounds,
    crop_year_of,
    days_between,
    in_crop_year,
    not_before,
    parse_date,
    require_in_crop_year,
    season_label,
)


@pytest.mark.parametrize(
    ("day", "year"),
    [
        (date(2025, 8, 1), 2025),
        (date(2025, 9, 14), 2025),
        (date(2025, 12, 31), 2025),
        (date(2026, 1, 4), 2025),
        (date(2026, 7, 31), 2025),
        (date(2026, 8, 1), 2026),
        (date(2025, 7, 31), 2024),
    ],
)
def test_the_crop_year_is_named_for_the_august_it_started_in(day: date, year: int) -> None:
    assert crop_year_of(day) == year


def test_the_bounds_are_both_inclusive_days() -> None:
    assert crop_year_bounds(2025) == (date(2025, 8, 1), date(2026, 7, 31))
    assert crop_year_bounds(2028) == (date(2028, 8, 1), date(2029, 7, 31))


def test_a_leap_february_does_not_move_the_bounds() -> None:
    assert crop_year_bounds(2027) == (date(2027, 8, 1), date(2028, 7, 31))


def test_the_bounds_and_the_lookup_agree_at_both_ends() -> None:
    first, last = crop_year_bounds(2025)
    assert crop_year_of(first) == 2025
    assert crop_year_of(last) == 2025
    assert in_crop_year(first, 2025)
    assert in_crop_year(last, 2025)
    assert not in_crop_year(last + timedelta(days=1), 2025)


def test_a_day_outside_the_year_is_refused_with_both_bounds_named() -> None:
    with pytest.raises(ValidationError, match="outside crop year 2025, which runs"):
        require_in_crop_year(date(2026, 8, 1), 2025)


def test_a_day_inside_the_year_comes_back_unchanged() -> None:
    assert require_in_crop_year(date(2025, 11, 2), 2025) == date(2025, 11, 2)


@pytest.mark.parametrize("year", [1999, 2100])
def test_a_crop_year_this_package_cannot_file_is_refused(year: int) -> None:
    with pytest.raises(ValidationError, match="between 2000 and 2099"):
        check_crop_year(year)


def test_a_bool_is_not_a_crop_year() -> None:
    with pytest.raises(ValidationError, match="whole year"):
        check_crop_year(True)


def test_the_folder_label_carries_both_years() -> None:
    assert season_label(2025) == "2025/26"
    assert season_label(2099) == "2099/00"


def test_a_date_reads_in_iso_and_only_in_iso() -> None:
    assert parse_date("2025-09-14") == date(2025, 9, 14)
    assert parse_date(" 2025-09-14 ") == date(2025, 9, 14)


@pytest.mark.parametrize("text", ["", "  ", "14/09/2025", "09-14-2025", "Sept 14", "2025-13-01"])
def test_a_date_in_any_other_order_is_refused(text: str) -> None:
    with pytest.raises(ValidationError):
        parse_date(text)


def test_a_date_before_the_floor_is_refused_with_both_dates_named() -> None:
    with pytest.raises(ValidationError, match="2025-09-01 is before 2025-09-14"):
        not_before(date(2025, 9, 1), date(2025, 9, 14))


def test_a_date_on_the_floor_passes() -> None:
    assert not_before(date(2025, 9, 14), date(2025, 9, 14)) == date(2025, 9, 14)


def test_days_between_is_signed() -> None:
    assert days_between(date(2025, 9, 1), date(2025, 9, 14)) == 13
    assert days_between(date(2025, 9, 14), date(2025, 9, 1)) == -13
    assert days_between(date(2025, 9, 1), date(2025, 9, 1)) == 0
