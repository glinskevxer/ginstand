"""A book with a grower and a field to gin off."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date

import pytest

from ginstand.store.book import Book


@pytest.fixture
def book() -> Iterator[Book]:
    with Book.create(":memory:", date(2025, 8, 4)) as book:
        yield book
