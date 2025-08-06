"""A book with a run's worth of bales already pressed."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest

from ginstand.model.bale import Bale
from ginstand.model.ginrun import GinRun
from ginstand.store.book import Book

PRESSED = date(2025, 10, 14)


@pytest.fixture
def book() -> Iterator[Book]:
    with Book.create(":memory:", date(2025, 8, 4)) as book:
        book.runs.add(GinRun(ref="GR-1", crop_year=2025, gin_code="41207", opened=PRESSED))
        for sequence in (61, 62, 63):
            book.bales.add(
                Bale(
                    tag=f"2541207{sequence:05d}",
                    run="GR-1",
                    pressed=PRESSED,
                    gross_pounds=512,
                    tare_pounds=22,
                    moisture_pct=Decimal("6.8"),
                )
            )
        yield book
