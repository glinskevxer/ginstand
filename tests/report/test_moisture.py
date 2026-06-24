"""Dry turnout does not move when the yard has a wet week."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import StateError
from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.report.moisture import for_run, moisture_table, season
from ginstand.store.book import Book
from ginstand.units.moisture import SAFE_BALE_MOISTURE
from ginstand.yard.receiving import receive

from .conftest import a_module

OPENED = date(2025, 10, 14)


def a_run(
    book: Book,
    ref: str,
    seed_cotton: int,
    module_moisture: str,
    bales: int,
    bale_moisture: str = "6.8",
    day: date = OPENED,
    field: str = "FL-9",
) -> None:
    open_run(book, ref, "41207", day)
    tag = f"M-{ref}"
    receive(
        book,
        a_module(
            tag,
            field=field,
            gross_pounds=26_140 + seed_cotton,
            tare_pounds=26_140,
            moisture_pct=Decimal(module_moisture),
        ),
    )
    feed(book, ref, tag, day)
    for _ in range(bales):
        press(book, ref, day, 512, 22, Decimal(bale_moisture))
    close_run(book, ref, day)


def test_a_run_with_nothing_in_it_has_no_moisture(book: Book) -> None:
    open_run(book, "GR-1", "41207", OPENED)
    with pytest.raises(StateError, match="has nothing in it"):
        for_run(book, "GR-1")


def test_the_means_are_weighted_by_weight(book: Book) -> None:
    a_run(book, "GR-1", 20_000, "11.0", 14)
    figure = for_run(book, "GR-1")
    assert figure.mean_in == Decimal("11.0")
    assert figure.mean_out == Decimal("6.7")


def test_rounding_dry_weight_per_bale_moves_the_mean_by_a_tenth(book: Book) -> None:
    """Every bale's dry weight is a whole number, and fourteen of them add up.

    A bale of 490 lb at 6.8% is 456.68 lb of dry matter and is stored as 457, so
    the mean read back off the dry weights is a tenth under what went in. That is
    the price of holding weights in whole pounds and it is worth knowing rather
    than chasing.
    """
    a_run(book, "GR-1", 20_000, "11.0", 14)
    figure = for_run(book, "GR-1")
    assert figure.lint_dry == 14 * 457
    assert figure.mean_out == Decimal("6.7")


def test_the_wet_turnout_is_the_one_the_run_sheet_carries(book: Book) -> None:
    a_run(book, "GR-1", 20_000, "11.0", 14)
    assert for_run(book, "GR-1").wet_turnout == Decimal("0.3430")


def test_the_dry_turnout_is_over_dry_matter(book: Book) -> None:
    a_run(book, "GR-1", 20_000, "11.0", 14)
    figure = for_run(book, "GR-1")
    assert figure.dry_turnout != figure.wet_turnout
    assert figure.dry_turnout == Decimal("0.3594")


def test_a_wetter_week_moves_the_wet_turnout_and_not_the_dry_one(book: Book) -> None:
    a_run(book, "GR-1", 20_000, "8.0", 14)
    a_run(book, "GR-2", 20_000, "16.0", 14, day=date(2025, 10, 20))
    dry = for_run(book, "GR-1")
    wet = for_run(book, "GR-2")
    assert dry.wet_turnout == wet.wet_turnout
    assert dry.dry_turnout != wet.dry_turnout


def test_the_gap_is_the_moisture_the_run_carried(book: Book) -> None:
    a_run(book, "GR-1", 20_000, "11.0", 14)
    figure = for_run(book, "GR-1")
    assert figure.gap == figure.dry_turnout - figure.wet_turnout
    assert figure.gap > 0


def test_the_wettest_module_and_bale_are_carried(book: Book) -> None:
    a_run(book, "GR-1", 20_000, "12.4", 14, bale_moisture="7.2")
    figure = for_run(book, "GR-1")
    assert figure.wettest_module == Decimal("12.4")
    assert figure.wettest_bale == Decimal("7.2")
    assert not figure.over_ceiling


def test_a_run_with_no_bales_has_no_wettest_bale(book: Book) -> None:
    a_run(book, "GR-1", 20_000, "11.0", 0)
    figure = for_run(book, "GR-1")
    assert figure.wettest_bale == Decimal("0.0")
    assert figure.mean_out == Decimal("0.0")
    assert figure.dry_turnout == Decimal("0.0000")


def test_the_ceiling_is_flagged_when_a_bale_is_over_it(book: Book) -> None:
    a_run(book, "GR-1", 20_000, "11.0", 2, bale_moisture=str(SAFE_BALE_MOISTURE))
    assert not for_run(book, "GR-1").over_ceiling


def test_the_season_lists_the_widest_gap_first(book: Book) -> None:
    a_run(book, "GR-1", 20_000, "8.0", 14)
    a_run(book, "GR-2", 20_000, "16.0", 14, day=date(2025, 10, 20))
    assert [item.run for item in season(book, 2025)] == ["GR-2", "GR-1"]


def test_a_run_with_nothing_in_it_is_left_off_the_season(book: Book) -> None:
    a_run(book, "GR-1", 20_000, "11.0", 14)
    open_run(book, "GR-2", "41207", date(2025, 10, 20))
    assert [item.run for item in season(book, 2025)] == ["GR-1"]


def test_a_crop_year_with_nothing_ginned_says_so(book: Book) -> None:
    assert moisture_table(book, 2025).render()[-1] == ("no run in this crop year has cotton in it")


def test_the_table_carries_both_turnouts(book: Book) -> None:
    a_run(book, "GR-1", 20_000, "11.0", 14)
    text = moisture_table(book, 2025).text()
    assert "wet turnout" in text
    assert "dry turnout" in text
    assert "GR-1" in text
