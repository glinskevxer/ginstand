"""A book stood up in memory, one per test."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from datetime import date

import pytest

from ginstand.store.migrations import apply_pending
from ginstand.store.sqlite import connect


@pytest.fixture
def book() -> Iterator[sqlite3.Connection]:
    connection = connect(":memory:")
    apply_pending(connection, date(2025, 8, 4))
    try:
        yield connection
    finally:
        connection.close()
