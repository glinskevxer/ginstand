"""Reading and writing yard holds.

The one open hold per module rule is a partial unique index in the schema rather
than a check here. That means it holds even for a book written by something
other than this code, and it means the store does not have to take a lock to
keep it true.
"""

from __future__ import annotations

import sqlite3
from datetime import date

from ginstand.errors import NotFoundError
from ginstand.ids import reference
from ginstand.model.hold import Hold, HoldReason
from ginstand.store.sqlite import as_date, as_optional_date


class HoldStore:
    """Every hold the yard has placed, open or lifted."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def place(self, hold: Hold) -> Hold:
        """Put a hold on a module and hand back the stored hold with its id."""
        cursor = self._connection.execute(
            "INSERT INTO yard_hold (module, reason, placed, placed_by, lifted, lifted_by, note)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                hold.module,
                str(hold.reason),
                hold.placed.isoformat(),
                hold.placed_by,
                None if hold.lifted is None else hold.lifted.isoformat(),
                hold.lifted_by,
                hold.note,
            ),
        )
        return self.get(int(cursor.lastrowid or 0))

    def save(self, hold: Hold) -> None:
        """Replace a hold that is already in the book, by its id."""
        if hold.hold_id <= 0:
            raise NotFoundError("hold", str(hold.hold_id))
        if self.find(hold.hold_id) is None:
            raise NotFoundError("hold", str(hold.hold_id))
        self._connection.execute(
            "UPDATE yard_hold SET module = ?, reason = ?, placed = ?, placed_by = ?,"
            " lifted = ?, lifted_by = ?, note = ? WHERE id = ?",
            (
                hold.module,
                str(hold.reason),
                hold.placed.isoformat(),
                hold.placed_by,
                None if hold.lifted is None else hold.lifted.isoformat(),
                hold.lifted_by,
                hold.note,
                hold.hold_id,
            ),
        )

    def find(self, hold_id: int) -> Hold | None:
        """The hold, or None."""
        row = self._connection.execute(
            "SELECT * FROM yard_hold WHERE id = ?", (hold_id,)
        ).fetchone()
        return None if row is None else _hold_from(row)

    def get(self, hold_id: int) -> Hold:
        """The hold. Raises if the book does not have it."""
        found = self.find(hold_id)
        if found is None:
            raise NotFoundError("hold", str(hold_id))
        return found

    def open_for(self, module: str) -> Hold | None:
        """The module's open hold, or None if it is free to gin."""
        key = reference(module, "module tag")
        row = self._connection.execute(
            "SELECT * FROM yard_hold WHERE module = ? AND lifted IS NULL", (key,)
        ).fetchone()
        return None if row is None else _hold_from(row)

    def history_for(self, module: str) -> tuple[Hold, ...]:
        """Every hold ever placed on a module, oldest first."""
        key = reference(module, "module tag")
        rows = self._connection.execute(
            "SELECT * FROM yard_hold WHERE module = ? ORDER BY placed, id", (key,)
        ).fetchall()
        return tuple(_hold_from(row) for row in rows)

    def all_open(self) -> tuple[Hold, ...]:
        """Every open hold in the yard, oldest first."""
        rows = self._connection.execute(
            "SELECT * FROM yard_hold WHERE lifted IS NULL ORDER BY placed, id"
        ).fetchall()
        return tuple(_hold_from(row) for row in rows)

    def open_on(self, day: date) -> tuple[Hold, ...]:
        """Every hold that was open on a given day, whether or not it still is."""
        rows = self._connection.execute(
            "SELECT * FROM yard_hold WHERE placed <= ?"
            " AND (lifted IS NULL OR lifted > ?) ORDER BY placed, id",
            (day.isoformat(), day.isoformat()),
        ).fetchall()
        return tuple(_hold_from(row) for row in rows)


def _hold_from(row: sqlite3.Row) -> Hold:
    return Hold(
        module=str(row["module"]),
        reason=HoldReason(str(row["reason"])),
        placed=as_date(row["placed"]),
        placed_by=str(row["placed_by"]),
        lifted=as_optional_date(row["lifted"]),
        lifted_by=str(row["lifted_by"]),
        note=str(row["note"]),
        hold_id=int(row["id"]),
    )
