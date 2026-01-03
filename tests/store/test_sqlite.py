"""A book opens with foreign keys on, and a transaction rolls the whole block back."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ginstand.errors import StateError
from ginstand.store.sqlite import (
    as_date,
    as_decimal,
    as_optional_date,
    as_text,
    connect,
    opened,
    table_names,
    transaction,
)


def test_foreign_keys_are_on_for_every_connection() -> None:
    with opened(":memory:") as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_a_file_book_runs_in_write_ahead_logging(tmp_path: Path) -> None:
    with opened(tmp_path / "book.sqlite3") as connection:
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_rows_come_back_by_column_name() -> None:
    with opened(":memory:") as connection:
        row = connection.execute("SELECT 1 AS bales").fetchone()
        assert row["bales"] == 1


def test_a_transaction_commits_when_the_block_finishes() -> None:
    with opened(":memory:") as connection:
        connection.execute("CREATE TABLE t (a INTEGER)")
        with transaction(connection):
            connection.execute("INSERT INTO t VALUES (1)")
        assert connection.execute("SELECT count(*) FROM t").fetchone()[0] == 1


def test_a_transaction_rolls_the_whole_block_back_on_an_error() -> None:
    def insert_then_fail(connection: sqlite3.Connection) -> None:
        with transaction(connection):
            connection.execute("INSERT INTO t VALUES (1)")
            raise ValueError("stop")

    with opened(":memory:") as connection:
        connection.execute("CREATE TABLE t (a INTEGER)")
        with pytest.raises(ValueError, match="stop"):
            insert_then_fail(connection)
        assert connection.execute("SELECT count(*) FROM t").fetchone()[0] == 0


def test_a_nested_transaction_is_refused_rather_than_flattened() -> None:
    def open_another(connection: sqlite3.Connection) -> None:
        with transaction(connection):
            pass

    with (
        opened(":memory:") as connection,
        transaction(connection),
        pytest.raises(StateError, match="already open"),
    ):
        open_another(connection)


def test_a_foreign_key_violation_is_raised_not_ignored() -> None:
    with opened(":memory:") as connection:
        connection.execute("CREATE TABLE parent (a INTEGER PRIMARY KEY)")
        connection.execute("CREATE TABLE child (a INTEGER REFERENCES parent(a))")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO child VALUES (9)")


@pytest.mark.parametrize(
    ("given", "stored"),
    [
        (date(2025, 10, 14), "2025-10-14"),
        (Decimal("52.0000"), "52.0000"),
        ("GR-1", "GR-1"),
        (490, 490),
        (None, None),
    ],
)
def test_values_go_into_the_book_as_text_a_person_can_read(given: object, stored: object) -> None:
    assert as_text(given) == stored  # type: ignore[arg-type]


def test_a_decimal_keeps_its_places_through_the_book() -> None:
    with opened(":memory:") as connection:
        connection.execute("CREATE TABLE r (rate TEXT)")
        connection.execute("INSERT INTO r VALUES (?)", (as_text(Decimal("52.0050")),))
        back = as_decimal(connection.execute("SELECT rate FROM r").fetchone()["rate"])
        assert back == Decimal("52.0050")
        assert str(back) == "52.0050"


def test_dates_read_back_as_dates() -> None:
    assert as_date("2025-10-14") == date(2025, 10, 14)
    assert as_optional_date(None) is None
    assert as_optional_date("2025-10-14") == date(2025, 10, 14)


@pytest.mark.parametrize("value", [None, 20251014, 1.5])
def test_a_column_that_is_not_an_iso_date_is_a_book_fault(value: object) -> None:
    with pytest.raises(StateError, match="expected an ISO date"):
        as_date(value)


@pytest.mark.parametrize("value", [None, 1.5, b"52"])
def test_a_column_that_is_not_a_decimal_is_a_book_fault(value: object) -> None:
    with pytest.raises(StateError, match="expected a decimal"):
        as_decimal(value)


def test_the_table_list_comes_back_in_name_order() -> None:
    with opened(":memory:") as connection:
        connection.execute("CREATE TABLE zeta (a INTEGER)")
        connection.execute("CREATE TABLE alpha (a INTEGER)")
        assert table_names(connection) == ("alpha", "zeta")


def test_the_opened_block_closes_the_connection() -> None:
    with opened(":memory:") as connection:
        assert connection.execute("SELECT 1").fetchone()[0] == 1
    with pytest.raises(sqlite3.ProgrammingError, match="Cannot operate on a closed"):
        connection.execute("SELECT 1")


def test_the_connection_closes_even_when_the_block_raises() -> None:
    held: list[sqlite3.Connection] = []

    def fail() -> None:
        with opened(":memory:") as connection:
            held.append(connection)
            raise ValueError("stop")

    with pytest.raises(ValueError, match="stop"):
        fail()
    with pytest.raises(sqlite3.ProgrammingError, match="Cannot operate on a closed"):
        held[0].execute("SELECT 1")


def test_a_plain_connection_can_still_be_opened_and_closed_by_hand() -> None:
    connection = connect(":memory:")
    try:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        connection.close()
