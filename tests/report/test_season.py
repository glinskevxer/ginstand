"""Season turnout is worked out over the season, not averaged over the runs."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import StateError
from ginstand.ginning.allocate import allocate
from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.ginning.seed import record_load
from ginstand.report.season import by_producer, by_run, summary, totals
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

from .conftest import a_module


def a_run(
    book: Book,
    ref: str,
    day: date,
    seed_cotton: int,
    bales: int,
    field: str = "FL-9",
    close: bool = True,
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
            harvested=date(2025, 9, 28),
            received=date(2025, 10, 2),
        ),
    )
    feed(book, ref, tag, day)
    for _ in range(bales):
        press(book, ref, day, 512, 22, Decimal("6.8"))
    if close:
        close_run(book, ref, day)
        allocate(book, ref, day)


def test_a_crop_year_with_no_runs_has_no_totals(book: Book) -> None:
    with pytest.raises(StateError, match="crop year 2025 has no gin runs"):
        totals(book, 2025)


def test_the_totals_add_the_runs_up(book: Book) -> None:
    a_run(book, "GR-1", date(2025, 10, 14), 20_000, 14)
    a_run(book, "GR-2", date(2025, 10, 20), 30_000, 20)
    season = totals(book, 2025)
    assert season.runs == 2
    assert season.modules == 2
    assert season.seed_cotton_pounds == 50_000
    assert season.bales == 34
    assert season.lint_pounds == 34 * 490


def test_the_season_turnout_is_not_the_mean_of_the_run_turnouts(book: Book) -> None:
    a_run(book, "GR-1", date(2025, 10, 14), 10_000, 5)
    a_run(book, "GR-2", date(2025, 10, 20), 50_000, 35)
    season = totals(book, 2025)
    over_the_season = season.lint_turnout
    mean_of_runs = (Decimal("0.2450") + Decimal("0.3430")) / 2
    assert over_the_season != mean_of_runs
    assert over_the_season == Decimal("0.3267")


def test_an_open_run_is_counted_and_flagged(book: Book) -> None:
    a_run(book, "GR-1", date(2025, 10, 14), 20_000, 3, close=False)
    season = totals(book, 2025)
    assert season.runs == 1
    assert season.open_runs == 1


def test_the_seed_turnout_uses_the_loads_booked(book: Book) -> None:
    a_run(book, "GR-1", date(2025, 10, 14), 20_000, 14)
    record_load(book, "GR-1", date(2025, 10, 14), 9_800)
    assert totals(book, 2025).seed_turnout == Decimal("0.4900")


def test_lint_per_bale_needs_a_bale(book: Book) -> None:
    a_run(book, "GR-1", date(2025, 10, 14), 20_000, 0, close=False)
    with pytest.raises(StateError, match="has no bales"):
        assert totals(book, 2025).lint_per_bale


def test_the_summary_reads_top_to_bottom(book: Book) -> None:
    a_run(book, "GR-1", date(2025, 10, 14), 20_000, 14)
    record_load(book, "GR-1", date(2025, 10, 14), 9_800)
    lines = summary(book, 2025)
    assert lines[0] == "Crop year 2025"
    assert "1 runs (0 open), 1 modules, 20,000 lb seed cotton" in lines[1]
    assert "14 bales" in lines[2]
    assert "lint turnout" in lines[3]
    assert "490 lb a bale" in lines[4]


def test_the_run_table_totals_the_season(book: Book) -> None:
    a_run(book, "GR-1", date(2025, 10, 14), 20_000, 14)
    a_run(book, "GR-2", date(2025, 10, 20), 30_000, 20)
    text = by_run(book, 2025).text()
    assert "GR-1" in text
    assert "GR-2" in text
    assert "50,000" in text
    assert "34" in text


def test_an_open_run_shows_open_in_the_closed_column(book: Book) -> None:
    a_run(book, "GR-1", date(2025, 10, 14), 20_000, 3, close=False)
    assert "open" in by_run(book, 2025).text()


def test_a_crop_year_with_no_runs_says_so_on_the_table(book: Book) -> None:
    assert by_run(book, 2019).render()[-1] == "no runs in this crop year"


def test_the_producer_table_splits_what_each_one_put_in(book: Book) -> None:
    a_run(book, "GR-1", date(2025, 10, 14), 20_000, 14, field="FL-9")
    a_run(book, "GR-2", date(2025, 10, 20), 30_000, 20, field="FL-5")
    text = by_producer(book, 2025).text()
    assert "P-12" in text
    assert "P-40" in text
    assert "20,000" in text
    assert "30,000" in text


def test_a_crop_year_nobody_ginned_says_so(book: Book) -> None:
    assert by_producer(book, 2019).render()[-1] == "nobody ginned in this crop year"
