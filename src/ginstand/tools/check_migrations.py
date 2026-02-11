"""The schema applies cleanly and every store's table is in it.

Three things go wrong with a migration list and none of them shows up in a test
of the code that reads the tables. A version can be skipped, so a book from last
season stops halfway. Two migrations can create the same table, so applying them
in order fails on a fresh book and passes on an old one. And a store can name a
table nobody ever created, which only fails the first time somebody queries it.

So this stands a book up from nothing and then asks every store whether its own
table is there.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

from ginstand.store import bales, cards, growers, land, modules, runs, warehouses
from ginstand.store.migrations import MIGRATIONS, apply_pending
from ginstand.store.repository import Repository
from ginstand.store.sqlite import connect, table_names
from ginstand.tools.base import Finding, run, source_root

STORES: tuple[type[Repository[Any]], ...] = (
    growers.ProducerStore,
    growers.LeaseStore,
    land.FarmStore,
    land.FieldStore,
    modules.ModuleStore,
    runs.RunStore,
    bales.BaleStore,
    cards.CardStore,
    warehouses.WarehouseStore,
    warehouses.ReceiptStore,
)

EXTRA_TABLES = {
    "run_module",
    "yard_hold",
    "bale_allocation",
    "allocation_carry",
    "seed_load",
    "recheck",
}
"""Tables no repository owns, because nothing reads them as whole records."""

SQLITE_TABLES = {"sqlite_sequence"}
"""Tables sqlite keeps for itself. AUTOINCREMENT creates the sequence table."""


def _path() -> Path:
    return source_root() / "store" / "migrations.py"


def findings() -> Iterator[Finding]:
    """Everything wrong with the schema."""
    path = _path()
    versions = [migration.version for migration in MIGRATIONS]
    if versions != list(range(1, len(versions) + 1)):
        yield Finding(path, 1, f"the versions are {versions}, expected 1 to {len(versions)}")
    names = [migration.name for migration in MIGRATIONS]
    for name in names:
        if not name.strip():
            yield Finding(path, 1, "a migration has no name")
    if len(set(names)) != len(names):
        yield Finding(path, 1, "two migrations share a name")

    connection = connect(":memory:")
    try:
        apply_pending(connection, date(2025, 8, 1))
        present = set(table_names(connection))
    finally:
        connection.close()

    for store in STORES:
        if store.table not in present:
            yield Finding(
                path,
                1,
                f"{store.__name__} reads {store.table}, which the schema has not got",
            )
    owned = {store.table for store in STORES} | EXTRA_TABLES | SQLITE_TABLES | {"schema_migration"}
    for table in sorted(present - owned):
        yield Finding(path, 1, f"the schema has {table}, which nothing reads")
    for table in sorted(EXTRA_TABLES - present):
        yield Finding(path, 1, f"{table} is expected and the schema has not got it")


def main() -> None:
    """Run the check."""
    run("check_migrations", findings())


if __name__ == "__main__":
    main()
