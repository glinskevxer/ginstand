"""Migrations run in order, once, and a book ahead of the code is refused."""

from __future__ import annotations

from datetime import date

import pytest

from ginstand.errors import StateError
from ginstand.store.migrations import (
    MIGRATION_TABLE,
    MIGRATIONS,
    applied,
    apply_pending,
    check_current,
    current_version,
    latest_version,
    pending,
)
from ginstand.store.sqlite import connect, table_names

DAY = date(2025, 8, 4)


def test_a_fresh_book_is_at_version_zero() -> None:
    with connect(":memory:") as connection:
        assert current_version(connection) == 0
        assert len(pending(connection)) == len(MIGRATIONS)


def test_applying_brings_the_book_to_the_version_the_code_writes() -> None:
    with connect(":memory:") as connection:
        done = apply_pending(connection, DAY)
        assert [m.version for m in done] == [m.version for m in MIGRATIONS]
        assert current_version(connection) == latest_version()
        assert pending(connection) == ()


def test_applying_twice_does_nothing_the_second_time() -> None:
    with connect(":memory:") as connection:
        apply_pending(connection, DAY)
        assert apply_pending(connection, DAY) == ()
        assert current_version(connection) == latest_version()


def test_the_day_recorded_is_the_day_that_was_passed_in() -> None:
    with connect(":memory:") as connection:
        apply_pending(connection, date(2025, 9, 1))
        assert {row[2] for row in applied(connection)} == {"2025-09-01"}


def test_the_record_of_what_was_applied_reads_back_in_order() -> None:
    with connect(":memory:") as connection:
        apply_pending(connection, DAY)
        versions = [row[0] for row in applied(connection)]
        assert versions == sorted(versions)
        assert versions == [m.version for m in MIGRATIONS]


def test_the_first_migration_stands_up_the_grower_records() -> None:
    with connect(":memory:") as connection:
        apply_pending(connection, DAY)
        names = table_names(connection)
        for table in ("producer", "lease", "farm", "field", MIGRATION_TABLE):
            assert table in names


def test_a_book_written_by_a_newer_version_is_refused() -> None:
    with connect(":memory:") as connection:
        apply_pending(connection, DAY)
        connection.execute(
            f"INSERT INTO {MIGRATION_TABLE} VALUES (?, ?, ?)",
            (latest_version() + 5, "from the future", DAY.isoformat()),
        )
        with pytest.raises(StateError, match="written by a newer version"):
            apply_pending(connection, DAY)


def test_the_current_check_names_both_versions() -> None:
    with connect(":memory:") as connection:
        with pytest.raises(StateError, match="is at schema version 0"):
            check_current(connection)
        apply_pending(connection, DAY)
        check_current(connection)


def test_the_versions_are_contiguous_and_start_at_one() -> None:
    versions = [m.version for m in MIGRATIONS]
    assert versions == list(range(1, len(MIGRATIONS) + 1))


def test_every_migration_has_a_name_and_at_least_one_statement() -> None:
    for migration in MIGRATIONS:
        assert migration.name.strip()
        assert migration.statements


def test_the_grower_tables_enforce_their_references() -> None:
    with connect(":memory:") as connection:
        apply_pending(connection, DAY)
        with pytest.raises(Exception, match="FOREIGN KEY"):
            connection.execute(
                "INSERT INTO farm (ref, producer, name) VALUES ('F-1', 'P-NOPE', 'Home')"
            )
