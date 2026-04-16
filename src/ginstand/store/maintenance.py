"""Backing the book up, and asking sqlite whether it is still sound.

A gin's book is one file on one machine in an office with a lot of dust in it.
Copying that file while the gin is running is not a backup, it is a copy of a
file that was being written to. Sqlite's own backup does it properly and it is
two lines, so there is no reason to do it the other way.

Two integrity questions, and they are different. The structural one asks whether
the file is a valid database. The foreign key one asks whether the records still
point at each other, which can go wrong even in a perfectly valid file: turning
foreign keys off for one statement is all it takes, and this package does that
in exactly one place, which is why the check exists.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ginstand.errors import StateError
from ginstand.store.book import Book
from ginstand.store.sqlite import connect, table_names


@dataclass(frozen=True, slots=True)
class Broken:
    """One record pointing at something that is not there."""

    table: str
    rowid: int
    points_at: str

    @property
    def line(self) -> str:
        """The finding as it prints."""
        return f"{self.table} row {self.rowid} points at {self.points_at}"


def backup(book: Book, path: str | Path) -> Path:
    """Copy the book to another file, through sqlite's own backup."""
    target = Path(path)
    if target.exists():
        raise StateError(f"{target} is already there, move it before backing up over it")
    target.parent.mkdir(parents=True, exist_ok=True)
    other = connect(target)
    try:
        book.connection.backup(other)
    finally:
        other.close()
    return target


def integrity(book: Book) -> tuple[str, ...]:
    """What sqlite says about the file's structure, empty when it is sound."""
    rows = book.connection.execute("PRAGMA integrity_check").fetchall()
    found = tuple(str(row[0]) for row in rows)
    return () if found == ("ok",) else found


def dangling(book: Book) -> tuple[Broken, ...]:
    """Every record pointing at something that is not there."""
    rows = book.connection.execute("PRAGMA foreign_key_check").fetchall()
    return tuple(
        Broken(table=str(row[0]), rowid=int(row[1] or 0), points_at=str(row[2])) for row in rows
    )


def counts(book: Book) -> dict[str, int]:
    """How many rows each table holds, in name order."""
    found = {}
    for table in table_names(book.connection):
        row = book.connection.execute(f"SELECT count(*) AS n FROM {table}").fetchone()
        found[table] = int(row["n"])
    return found


def compact(book: Book) -> None:
    """Squeeze the file down after a season's deletions."""
    if book.connection.in_transaction:
        raise StateError("the book has a transaction open, so it cannot be compacted")
    book.connection.execute("VACUUM")


def check(book: Book) -> tuple[str, ...]:
    """Everything wrong with the book, structure first."""
    lines = list(integrity(book))
    lines.extend(item.line for item in dangling(book))
    return tuple(lines)
