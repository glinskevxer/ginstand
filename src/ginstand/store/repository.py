"""What every store in this package does the same way.

Eight stores had the same four methods written out eight times: find, get,
exists and list all. They were not quite identical, which was the problem. The
module store looked its key up without normalising it for a while and nobody
noticed, because there was no one place to look at to see that it was different.

Subclasses say what table they are, what the key column is called, what a record
is called when it is missing, and how to turn a row into a record. Ordering is a
class attribute because it varies and it is part of what a store promises: the
module store hands modules back oldest first and that is not an accident of the
query.
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from typing import ClassVar, Generic, TypeVar

from ginstand.errors import NotFoundError
from ginstand.ids import reference

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """One kind of record, read out of one table."""

    table: ClassVar[str]
    kind: ClassVar[str]
    key_column: ClassVar[str] = "ref"
    order_by: ClassVar[str] = "ref"

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    @abstractmethod
    def _from_row(self, row: sqlite3.Row) -> T:
        """Turn a row into the record it stands for."""

    def _key(self, value: str) -> str:
        """Normalise a key the way this store's references are written."""
        return reference(value, self.kind)

    def find(self, ref: str) -> T | None:
        """The record, or None if the book does not have it."""
        row = self._connection.execute(
            f"SELECT * FROM {self.table} WHERE {self.key_column} = ?", (self._key(ref),)
        ).fetchone()
        return None if row is None else self._from_row(row)

    def get(self, ref: str) -> T:
        """The record. Raises if the book does not have it."""
        found = self.find(ref)
        if found is None:
            raise NotFoundError(self.kind, self._key(ref))
        return found

    def exists(self, ref: str) -> bool:
        """Whether the book has this record."""
        return self.find(ref) is not None

    def list_all(self) -> tuple[T, ...]:
        """Every record, in this store's own order."""
        rows = self._connection.execute(
            f"SELECT * FROM {self.table} ORDER BY {self.order_by}"
        ).fetchall()
        return tuple(self._from_row(row) for row in rows)

    def count(self) -> int:
        """How many records the store holds."""
        row = self._connection.execute(f"SELECT count(*) AS n FROM {self.table}").fetchone()
        return int(row["n"])

    def _select(self, where: str, parameters: tuple[object, ...]) -> tuple[T, ...]:
        """Every record matching a condition, in this store's own order."""
        rows = self._connection.execute(
            f"SELECT * FROM {self.table} WHERE {where} ORDER BY {self.order_by}", parameters
        ).fetchall()
        return tuple(self._from_row(row) for row in rows)
