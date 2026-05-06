"""The season report tables."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ginstand.ginning.allocate import allocate
from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.ginning.seed import record_load
from ginstand.report.season import by_producer, by_run, summary
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
    """Open a run, feed one module into it, press bales and close it."""
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


def test_an_empty_run_table_prints_no_totals(book: Book) -> None:
    lines = by_run(book, 2019).render()
    assert lines[-1] == "no runs in this crop year"


def test_an_empty_producer_table_prints_no_totals(book: Book) -> None:
    lines = by_producer(book, 2019).render()
    assert lines[-1] == "nobody ginned in this crop year"
