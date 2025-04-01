"""The book's schema, as an ordered list of migrations.

Each migration is a version number, a name and the statements that take the book
from the version before it to that version. They are applied in order and
recorded, so a book from last season can be opened by this season's code and
brought forward without anybody having to remember what changed.

A book that is ahead of the code is refused rather than used. That happens when
two versions of this package share a file, and reading it with the older one
would quietly ignore columns the newer one relies on.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from ginstand.errors import StateError

MIGRATION_TABLE = "schema_migration"


@dataclass(frozen=True, slots=True)
class Migration:
    """One step of the schema."""

    version: int
    name: str
    statements: tuple[str, ...]


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        version=1,
        name="producers, leases, farms and fields",
        statements=(
            """
            CREATE TABLE producer (
                ref        TEXT PRIMARY KEY,
                name       TEXT NOT NULL,
                address    TEXT NOT NULL DEFAULT '',
                phone      TEXT NOT NULL DEFAULT '',
                ccc_number TEXT NOT NULL DEFAULT ''
            )
            """,
            """
            CREATE TABLE lease (
                ref            TEXT PRIMARY KEY,
                tenant         TEXT NOT NULL REFERENCES producer(ref),
                kind           TEXT NOT NULL,
                landlord       TEXT NOT NULL DEFAULT '',
                landlord_share TEXT NOT NULL DEFAULT '0'
            )
            """,
            "CREATE INDEX lease_by_tenant ON lease(tenant)",
            """
            CREATE TABLE farm (
                ref        TEXT PRIMARY KEY,
                producer   TEXT NOT NULL REFERENCES producer(ref),
                name       TEXT NOT NULL,
                fsa_number TEXT NOT NULL DEFAULT '',
                county     TEXT NOT NULL DEFAULT ''
            )
            """,
            "CREATE INDEX farm_by_producer ON farm(producer)",
            """
            CREATE TABLE field (
                ref       TEXT PRIMARY KEY,
                farm      TEXT NOT NULL REFERENCES farm(ref),
                name      TEXT NOT NULL,
                acres     TEXT NOT NULL,
                lease     TEXT NOT NULL REFERENCES lease(ref),
                variety   TEXT NOT NULL DEFAULT '',
                irrigated INTEGER NOT NULL DEFAULT 0
            )
            """,
            "CREATE INDEX field_by_farm ON field(farm)",
        ),
    ),
    Migration(
        version=2,
        name="the module yard and the gin run",
        statements=(
            """
            CREATE TABLE module (
                tag           TEXT PRIMARY KEY,
                field         TEXT NOT NULL REFERENCES field(ref),
                kind          TEXT NOT NULL,
                harvested     TEXT NOT NULL,
                received      TEXT NOT NULL,
                gross_pounds  INTEGER NOT NULL,
                tare_pounds   INTEGER NOT NULL,
                moisture_pct  TEXT NOT NULL,
                wrap          TEXT NOT NULL DEFAULT 'none',
                variety       TEXT NOT NULL DEFAULT '',
                note          TEXT NOT NULL DEFAULT ''
            )
            """,
            "CREATE INDEX module_by_field ON module(field)",
            "CREATE INDEX module_by_received ON module(received)",
            """
            CREATE TABLE gin_run (
                ref        TEXT PRIMARY KEY,
                crop_year  INTEGER NOT NULL,
                gin_code   TEXT NOT NULL,
                opened     TEXT NOT NULL,
                closed     TEXT,
                shift      TEXT NOT NULL DEFAULT '',
                note       TEXT NOT NULL DEFAULT ''
            )
            """,
            "CREATE INDEX gin_run_by_crop_year ON gin_run(crop_year)",
            """
            CREATE TABLE run_module (
                run      TEXT NOT NULL REFERENCES gin_run(ref),
                module   TEXT NOT NULL REFERENCES module(tag),
                position INTEGER NOT NULL,
                fed_on   TEXT NOT NULL,
                PRIMARY KEY (run, module)
            )
            """,
            "CREATE UNIQUE INDEX run_module_position ON run_module(run, position)",
            "CREATE UNIQUE INDEX run_module_once ON run_module(module)",
        ),
    ),
)


def latest_version() -> int:
    """The version this code writes."""
    return MIGRATIONS[-1].version if MIGRATIONS else 0


def _ensure_migration_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
            version    INTEGER PRIMARY KEY,
            name       TEXT NOT NULL,
            applied_on TEXT NOT NULL
        )
        """
    )


def current_version(connection: sqlite3.Connection) -> int:
    """The version the book is at. Zero for a book with no schema yet."""
    _ensure_migration_table(connection)
    row = connection.execute(f"SELECT max(version) AS v FROM {MIGRATION_TABLE}").fetchone()
    return int(row["v"] or 0)


def applied(connection: sqlite3.Connection) -> tuple[tuple[int, str, str], ...]:
    """Every migration this book has had, oldest first."""
    _ensure_migration_table(connection)
    rows = connection.execute(
        f"SELECT version, name, applied_on FROM {MIGRATION_TABLE} ORDER BY version"
    ).fetchall()
    return tuple((int(r["version"]), str(r["name"]), str(r["applied_on"])) for r in rows)


def pending(connection: sqlite3.Connection) -> tuple[Migration, ...]:
    """The migrations this book still needs."""
    at = current_version(connection)
    return tuple(m for m in MIGRATIONS if m.version > at)


def apply_pending(connection: sqlite3.Connection, on: date) -> tuple[Migration, ...]:
    """Bring the book up to the version this code writes.

    The day is passed in rather than read off the clock, so a book restored from
    a backup and replayed records the day the office says it was done.
    """
    at = current_version(connection)
    if at > latest_version():
        raise StateError(
            f"the book is at schema version {at} and this code writes "
            f"{latest_version()}, so it was written by a newer version"
        )
    done = []
    for migration in pending(connection):
        for statement in migration.statements:
            connection.execute(statement)
        connection.execute(
            f"INSERT INTO {MIGRATION_TABLE} (version, name, applied_on) VALUES (?, ?, ?)",
            (migration.version, migration.name, on.isoformat()),
        )
        done.append(migration)
    return tuple(done)


def check_current(connection: sqlite3.Connection) -> None:
    """Raise unless the book is at exactly the version this code writes."""
    at = current_version(connection)
    if at != latest_version():
        raise StateError(f"the book is at schema version {at}, this code writes {latest_version()}")
