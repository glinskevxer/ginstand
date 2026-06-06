"""The producer's printed page."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.ginning.allocate import allocate
from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.report.producer import page, run_table
from ginstand.settle.season import for_producer
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

from .conftest import a_module

OPENED = date(2025, 10, 14)


@pytest.fixture
def ginned(book: Book) -> Book:
    open_run(book, "GR-1", "41207", OPENED)
    for tag, field_ref, net in (("M-1", "FL-9", 20_000), ("M-2", "FL-5", 10_000)):
        receive(
            book,
            a_module(tag, field=field_ref, gross_pounds=26_140 + net, tare_pounds=26_140),
        )
        feed(book, "GR-1", tag, OPENED)
    for _ in range(9):
        press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
    close_run(book, "GR-1", OPENED)
    allocate(book, "GR-1", OPENED)
    return book


def test_the_run_table_totals_the_season(ginned: Book) -> None:
    season = for_producer(ginned, "P-12", 2025)
    text = run_table(season).text()
    assert "GR-1" in text
    assert "20,000" in text


def test_the_page_carries_the_totals_and_the_table(ginned: Book) -> None:
    lines = page(ginned, "P-12", 2025)
    assert lines[0].startswith("P-12  Aldys Brothers  crop year 2025")
    assert any(line.startswith("Runs for P-12") for line in lines)


def test_a_producer_with_nothing_ginned_has_no_page(ginned: Book) -> None:
    from ginstand.errors import StateError

    with pytest.raises(StateError, match="no settled run in crop year 2026"):
        page(ginned, "P-12", 2026)
