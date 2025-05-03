"""The book: one handle onto every store, and the two ways to get one.

``Book.create`` stands a new book up and applies the schema. ``Book.open``
opens one that exists and refuses it if the schema is not the version this code
writes. Keeping those apart matters because opening a path that does not exist
creates an empty sqlite file, and an empty file that silently becomes a new
season's book is how a gin loses a week of tickets.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from types import TracebackType

from ginstand.errors import StateError
from ginstand.store.bales import BaleStore
from ginstand.store.cards import CardStore
from ginstand.store.growers import LeaseStore, ProducerStore
from ginstand.store.holds import HoldStore
from ginstand.store.land import FarmStore, FieldStore
from ginstand.store.migrations import apply_pending, check_current, current_version
from ginstand.store.modules import ModuleStore
from ginstand.store.runs import RunStore
from ginstand.store.sqlite import IN_MEMORY, connect, transaction


class Book:
    """Every record the gin office keeps, behind one handle."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection
        self.producers = ProducerStore(connection)
        self.leases = LeaseStore(connection)
        self.farms = FarmStore(connection)
        self.fields = FieldStore(connection)
        self.modules = ModuleStore(connection)
        self.runs = RunStore(connection)
        self.bales = BaleStore(connection)
        self.cards = CardStore(connection)
        self.holds = HoldStore(connection)

    @classmethod
    def create(cls, path: str | Path, on: date) -> Book:
        """Stand up a new book and apply the schema."""
        target = str(path)
        if target != IN_MEMORY and Path(target).exists():
            raise StateError(f"{target} is already there, open it rather than creating it")
        connection = connect(target)
        apply_pending(connection, on)
        return cls(connection)

    @classmethod
    def open(cls, path: str | Path) -> Book:
        """Open a book that exists. Refuses one at the wrong schema version."""
        target = str(path)
        if target != IN_MEMORY and not Path(target).exists():
            raise StateError(f"there is no book at {target}")
        connection = connect(target)
        try:
            check_current(connection)
        except StateError:
            connection.close()
            raise
        return cls(connection)

    @classmethod
    def open_or_upgrade(cls, path: str | Path, on: date) -> Book:
        """Open a book and bring an older one forward."""
        target = str(path)
        if target != IN_MEMORY and not Path(target).exists():
            raise StateError(f"there is no book at {target}")
        connection = connect(target)
        apply_pending(connection, on)
        return cls(connection)

    @property
    def connection(self) -> sqlite3.Connection:
        """The connection underneath, for a report that needs its own query."""
        return self._connection

    @property
    def schema_version(self) -> int:
        """The schema version this book is at."""
        return current_version(self._connection)

    @contextmanager
    def writing(self) -> Iterator[Book]:
        """Run a block of writes as one transaction."""
        with transaction(self._connection):
            yield self

    def close(self) -> None:
        """Close the book."""
        self._connection.close()

    def __enter__(self) -> Book:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()
