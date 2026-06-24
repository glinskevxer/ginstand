"""Reading a book back in from the CSV the export wrote.

This is for rebuilding a book from the files, which happens twice: after a disk
goes, and when the accountant sends back a season the office has lost. It is not
for editing records in a spreadsheet and loading them again, which is why it
refuses to write into a table that already has rows in it. A partial merge is a
thing somebody thinks they want at four in the afternoon and regrets on the
statement run.

Order matters. A field points at a farm and a farm at a producer, so the tables
go in the order the schema created them and not in alphabetical order, which is
the order the files are sitting in.

Nothing here parses a value. The export wrote what sqlite held and the import
puts it back, so a date that was text is text again and a decimal that was text
keeps its places. Validation is the model layer's job and it happens when
something reads the row, which is where the message is useful.

One thing does have to be decided, because CSV cannot tell an empty string from
a null and both come back as an empty cell. The column settles it: an empty cell
in a column the schema declares NOT NULL is an empty string, and in a column that
allows null it is a null. That is right for this schema, where a nullable column
is a date that has not happened yet and never an empty string.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from ginstand.errors import StateError
from ginstand.store.book import Book
from ginstand.store.export import SKIP, tables
from ginstand.store.migrations import MIGRATIONS


@dataclass(frozen=True, slots=True)
class Loaded:
    """One file that went in."""

    table: str
    rows: int

    @property
    def line(self) -> str:
        """The line the import prints."""
        return f"{self.table:<18} {self.rows:>6} rows"


def creation_order() -> tuple[str, ...]:
    """Every table, in the order the migrations created it.

    Alphabetical order puts bale before gin_run, and a bale points at a run, so
    reading the files in the order they happen to sort in fails on the first
    foreign key. The migrations already know the right order.
    """
    order: list[str] = []
    for migration in MIGRATIONS:
        for statement in migration.statements:
            words = statement.split()
            if len(words) > 2 and words[0].upper() == "CREATE" and words[1].upper() == "TABLE":
                name = words[2]
                if name not in SKIP:
                    order.append(name)
    return tuple(order)


def columns_of(book: Book, table: str) -> tuple[str, ...]:
    """The columns a table has, in the order sqlite holds them."""
    return tuple(name for name, _ in _column_info(book, table))


def nullable(book: Book, table: str) -> tuple[bool, ...]:
    """Whether each column allows a null, in column order."""
    return tuple(allows for _, allows in _column_info(book, table))


def _column_info(book: Book, table: str) -> tuple[tuple[str, bool], ...]:
    rows = book.connection.execute(f"PRAGMA table_info({table})").fetchall()
    return tuple((str(row["name"]), not int(row["notnull"])) for row in rows)


def read_table(book: Book, table: str, path: Path) -> Loaded:
    """Read one file into one empty table."""
    if table not in tables(book):
        raise StateError(f"the book has no table called {table}")
    standing = book.connection.execute(f"SELECT count(*) AS n FROM {table}").fetchone()
    if int(standing["n"]):
        raise StateError(
            f"{table} already has {standing['n']} rows, and this reads into an empty table"
        )
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            raise StateError(f"{path.name} has no header row") from None
        wanted = columns_of(book, table)
        if tuple(header) != wanted:
            raise StateError(
                f"{path.name} has columns {', '.join(header)} and {table} has {', '.join(wanted)}"
            )
        allows_null = nullable(book, table)
        placeholders = ", ".join("?" for _ in wanted)
        names = ", ".join(wanted)
        rows = 0
        for row in reader:
            if len(row) != len(wanted):
                raise StateError(
                    f"{path.name} row {rows + 2} has {len(row)} cells and "
                    f"{table} has {len(wanted)} columns"
                )
            book.connection.execute(
                f"INSERT INTO {table} ({names}) VALUES ({placeholders})",
                tuple(
                    None if cell == "" and allows else cell
                    for cell, allows in zip(row, allows_null, strict=True)
                ),
            )
            rows += 1
    return Loaded(table=table, rows=rows)


def read_all(book: Book, folder: Path) -> tuple[Loaded, ...]:
    """Read a whole folder of files back into an empty book."""
    if not folder.is_dir():
        raise StateError(f"there is no folder at {folder}")
    loaded = []
    for table in creation_order():
        path = folder / f"{table}.csv"
        if not path.is_file():
            continue
        loaded.append(read_table(book, table, path))
    if not loaded:
        raise StateError(f"{folder} has no table files in it")
    return tuple(loaded)
