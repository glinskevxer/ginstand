"""Writing the book out as CSV, and reading the files back to check them.

The office's accountant does not have this package and is not going to. What
they have is a spreadsheet, so once a season the book goes out as one CSV per
table with a header row.

The tables are found by asking the book rather than by listing them here. A list
would go stale the first time a migration added a table, and the table that got
missed would be the new one nobody has a habit of checking.

Reading back is a check rather than an import. It counts what it wrote and
compares, because a full disk does not raise, it writes a short file.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from ginstand.errors import StateError
from ginstand.store.book import Book
from ginstand.store.migrations import MIGRATION_TABLE
from ginstand.store.sqlite import table_names

SKIP = {MIGRATION_TABLE, "sqlite_sequence"}
"""Tables that are the book's own machinery rather than the office's records."""


@dataclass(frozen=True, slots=True)
class Written:
    """One file that went out."""

    table: str
    path: Path
    rows: int

    @property
    def line(self) -> str:
        """The line the export prints."""
        return f"{self.table:<18} {self.rows:>6} rows  {self.path.name}"


def tables(book: Book) -> tuple[str, ...]:
    """Every table worth writing out, in name order."""
    return tuple(name for name in table_names(book.connection) if name not in SKIP)


def write_table(book: Book, table: str, folder: Path) -> Written:
    """Write one table out as CSV, header row first."""
    cursor = book.connection.execute(f"SELECT * FROM {table}")
    columns = [description[0] for description in cursor.description]
    path = folder / f"{table}.csv"
    rows = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for row in cursor:
            writer.writerow(["" if value is None else value for value in row])
            rows += 1
    return Written(table=table, path=path, rows=rows)


def write_all(book: Book, folder: Path) -> tuple[Written, ...]:
    """Write every table out into a folder."""
    if folder.exists() and not folder.is_dir():
        raise StateError(f"{folder} is a file, not a folder to write into")
    folder.mkdir(parents=True, exist_ok=True)
    return tuple(write_table(book, table, folder) for table in tables(book))


def read_back(written: Written) -> int:
    """How many rows a written file actually has, header row not counted."""
    if not written.path.is_file():
        raise StateError(f"{written.path} is not there")
    with written.path.open(newline="", encoding="utf-8") as handle:
        return max(sum(1 for _ in csv.reader(handle)) - 1, 0)


def verify(written: tuple[Written, ...]) -> tuple[str, ...]:
    """Check every file has the rows the export said it wrote."""
    problems = []
    for item in written:
        found = read_back(item)
        if found != item.rows:
            problems.append(f"{item.path.name} has {found} rows and the export wrote {item.rows}")
    return tuple(problems)
