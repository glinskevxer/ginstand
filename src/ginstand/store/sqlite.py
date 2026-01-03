"""Opening a book, and the two habits every connection needs.

Foreign keys are off by default in sqlite and have to be turned on per
connection. Write ahead logging keeps a long report from blocking the scale
house. Both are set here so no caller has to remember them.

Use :func:`opened` rather than putting :func:`connect` in a ``with``. A sqlite
connection is a context manager for its *transaction*, not for itself: leaving
its block commits and does not close. Python 3.13 warns about the connection
that is left behind and 3.12 does not, so a leak written on one of them is
found on the other.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from ginstand.errors import StateError

IN_MEMORY = ":memory:"


def connect(path: str | Path) -> sqlite3.Connection:
    """Open a book and set the pragmas every connection needs."""
    target = str(path)
    connection = sqlite3.connect(target, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    if target != IN_MEMORY:
        connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


@contextmanager
def opened(path: str | Path) -> Iterator[sqlite3.Connection]:
    """Open a book and close it when the block ends.

    This is what a ``with`` around a connection ought to mean and does not.
    """
    connection = connect(path)
    try:
        yield connection
    finally:
        connection.close()


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run a block as one transaction, rolling back on any error.

    Nested use is refused rather than silently flattened. A caller that thinks
    it owns a transaction and does not is the sort of thing that shows up as
    half a gin run in the book six weeks later.
    """
    if connection.in_transaction:
        raise StateError("a transaction is already open on this connection")
    connection.execute("BEGIN")
    try:
        yield connection
    except BaseException:
        connection.execute("ROLLBACK")
        raise
    connection.execute("COMMIT")


def as_text(value: date | Decimal | str | int | None) -> str | int | None:
    """Turn a value into what goes in the column.

    Dates and decimals go in as text. Storing a Decimal as a float loses the
    fourth place on a rate, and storing a date through an adapter hides the
    format from anyone reading the file.
    """
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def as_date(value: Any) -> date:
    """Read a date column back."""
    if not isinstance(value, str):
        raise StateError(f"expected an ISO date in the book, found {value!r}")
    return date.fromisoformat(value)


def as_optional_date(value: Any) -> date | None:
    """Read a nullable date column back."""
    return None if value is None else as_date(value)


def as_decimal(value: Any) -> Decimal:
    """Read a decimal column back."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, str):
        return Decimal(value)
    raise StateError(f"expected a decimal in the book, found {value!r}")


def table_names(connection: sqlite3.Connection) -> tuple[str, ...]:
    """Every table in the book, in name order."""
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
    ).fetchall()
    return tuple(str(row["name"]) for row in rows)
