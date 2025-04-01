"""Reading and writing modules.

A module is written once, when it crosses the scale, and after that it is read.
There is an update here because a ticket does get corrected, but corrections are
rare and the office wants them to look like work rather than like typing, so the
method is named for what it is.

The queries are the ones the yard actually asks: what came in on a day, what is
still waiting to be ginned, and what came off one field.
"""

from __future__ import annotations

import sqlite3
from datetime import date

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.ids import reference
from ginstand.model.module import Module, ModuleKind, WrapKind
from ginstand.store.sqlite import as_date, as_decimal


class ModuleStore:
    """Every module the gin has taken in."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, module: Module) -> None:
        """Weigh a module into the book. Raises if the tag is taken."""
        if self.exists(module.tag):
            raise DuplicateError("module", module.tag)
        self._connection.execute(
            "INSERT INTO module (tag, field, kind, harvested, received, gross_pounds,"
            " tare_pounds, moisture_pct, wrap, variety, note)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                module.tag,
                module.field,
                str(module.kind),
                module.harvested.isoformat(),
                module.received.isoformat(),
                module.gross_pounds,
                module.tare_pounds,
                str(module.moisture_pct),
                str(module.wrap),
                module.variety,
                module.note,
            ),
        )

    def correct(self, module: Module) -> None:
        """Replace a module's ticket after a correction. Raises if it is not there."""
        if not self.exists(module.tag):
            raise NotFoundError("module", module.tag)
        self._connection.execute(
            "UPDATE module SET field = ?, kind = ?, harvested = ?, received = ?,"
            " gross_pounds = ?, tare_pounds = ?, moisture_pct = ?, wrap = ?, variety = ?,"
            " note = ? WHERE tag = ?",
            (
                module.field,
                str(module.kind),
                module.harvested.isoformat(),
                module.received.isoformat(),
                module.gross_pounds,
                module.tare_pounds,
                str(module.moisture_pct),
                str(module.wrap),
                module.variety,
                module.note,
                module.tag,
            ),
        )

    def find(self, tag: str) -> Module | None:
        """The module, or None."""
        key = reference(tag, "module tag")
        row = self._connection.execute("SELECT * FROM module WHERE tag = ?", (key,)).fetchone()
        return None if row is None else _module_from(row)

    def get(self, tag: str) -> Module:
        """The module. Raises if the book does not have it."""
        found = self.find(tag)
        if found is None:
            raise NotFoundError("module", reference(tag, "module tag"))
        return found

    def exists(self, tag: str) -> bool:
        """Whether the book has a module under this tag."""
        return self.find(tag) is not None

    def list_all(self) -> tuple[Module, ...]:
        """Every module, oldest received first."""
        rows = self._connection.execute("SELECT * FROM module ORDER BY received, tag").fetchall()
        return tuple(_module_from(row) for row in rows)

    def received_on(self, day: date) -> tuple[Module, ...]:
        """Every module weighed in on one day."""
        rows = self._connection.execute(
            "SELECT * FROM module WHERE received = ? ORDER BY tag", (day.isoformat(),)
        ).fetchall()
        return tuple(_module_from(row) for row in rows)

    def for_field(self, field: str) -> tuple[Module, ...]:
        """Every module off one field."""
        key = reference(field, "field")
        rows = self._connection.execute(
            "SELECT * FROM module WHERE field = ? ORDER BY received, tag", (key,)
        ).fetchall()
        return tuple(_module_from(row) for row in rows)

    def unginned(self) -> tuple[Module, ...]:
        """Every module that has not been fed into a run yet."""
        rows = self._connection.execute(
            "SELECT m.* FROM module m"
            " LEFT JOIN run_module r ON r.module = m.tag"
            " WHERE r.module IS NULL"
            " ORDER BY m.received, m.tag"
        ).fetchall()
        return tuple(_module_from(row) for row in rows)

    def seed_cotton_pounds(self) -> int:
        """Every pound of seed cotton the book knows about."""
        row = self._connection.execute(
            "SELECT coalesce(sum(gross_pounds - tare_pounds), 0) AS net FROM module"
        ).fetchone()
        return int(row["net"])


def _module_from(row: sqlite3.Row) -> Module:
    return Module(
        tag=str(row["tag"]),
        field=str(row["field"]),
        kind=ModuleKind(str(row["kind"])),
        harvested=as_date(row["harvested"]),
        received=as_date(row["received"]),
        gross_pounds=int(row["gross_pounds"]),
        tare_pounds=int(row["tare_pounds"]),
        moisture_pct=as_decimal(row["moisture_pct"]),
        wrap=WrapKind(str(row["wrap"])),
        variety=str(row["variety"]),
        note=str(row["note"]),
    )
