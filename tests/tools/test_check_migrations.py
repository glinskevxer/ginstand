"""The migration check, and the schema passing it."""

from __future__ import annotations

from datetime import date

from ginstand.store.migrations import MIGRATIONS, apply_pending
from ginstand.store.sqlite import connect, table_names
from ginstand.tools.check_migrations import EXTRA_TABLES, STORES, findings


def test_the_schema_is_clean() -> None:
    assert list(findings()) == []


def test_every_store_names_a_table_the_schema_creates() -> None:
    connection = connect(":memory:")
    apply_pending(connection, date(2025, 8, 1))
    present = set(table_names(connection))
    connection.close()
    for store in STORES:
        assert store.table in present


def test_every_table_with_no_store_is_listed_on_purpose() -> None:
    connection = connect(":memory:")
    apply_pending(connection, date(2025, 8, 1))
    present = set(table_names(connection))
    connection.close()
    unowned = present - {store.table for store in STORES}
    unowned -= {"schema_migration", "sqlite_sequence"}
    assert unowned == EXTRA_TABLES


def test_the_versions_are_contiguous() -> None:
    versions = [migration.version for migration in MIGRATIONS]
    assert versions == list(range(1, len(versions) + 1))


def test_every_migration_has_a_name_of_its_own() -> None:
    names = [migration.name for migration in MIGRATIONS]
    assert len(set(names)) == len(names)
    assert all(name.strip() for name in names)


def test_no_two_migrations_create_the_same_table() -> None:
    created: list[str] = []
    for migration in MIGRATIONS:
        for statement in migration.statements:
            words = statement.split()
            if len(words) > 2 and words[0].upper() == "CREATE" and words[1].upper() == "TABLE":
                created.append(words[2])
    assert len(set(created)) == len(created)


def test_the_schema_applies_from_nothing() -> None:
    connection = connect(":memory:")
    applied = apply_pending(connection, date(2025, 8, 1))
    connection.close()
    assert len(applied) == len(MIGRATIONS)
