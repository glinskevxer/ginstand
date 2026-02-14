"""Reading and writing recheck requests.

One request open per bale at a time, held by a partial unique index the same way
the yard's holds are. Two open requests against one card would mean two answers
coming back for one sample, and only one of them can be the card.
"""

from __future__ import annotations

import sqlite3
from datetime import date

from ginstand.errors import NotFoundError
from ginstand.ids import bale_tag
from ginstand.model.recheck import Recheck, RecheckOutcome, RecheckReason
from ginstand.store.sqlite import as_date, as_optional_date


class RecheckStore:
    """Every recheck the gin has asked for, open or answered."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def request(self, recheck: Recheck) -> Recheck:
        """Send a request and hand back the stored one with its id."""
        cursor = self._connection.execute(
            "INSERT INTO recheck (tag, requested, reason, requested_by, settled,"
            " outcome, note) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                recheck.tag,
                recheck.requested.isoformat(),
                str(recheck.reason),
                recheck.requested_by,
                None if recheck.settled is None else recheck.settled.isoformat(),
                str(recheck.outcome),
                recheck.note,
            ),
        )
        return self.get(int(cursor.lastrowid or 0))

    def save(self, recheck: Recheck) -> None:
        """Replace a request that is already in the book, by its id."""
        if recheck.recheck_id <= 0 or self.find(recheck.recheck_id) is None:
            raise NotFoundError("recheck", str(recheck.recheck_id))
        self._connection.execute(
            "UPDATE recheck SET tag = ?, requested = ?, reason = ?, requested_by = ?,"
            " settled = ?, outcome = ?, note = ? WHERE id = ?",
            (
                recheck.tag,
                recheck.requested.isoformat(),
                str(recheck.reason),
                recheck.requested_by,
                None if recheck.settled is None else recheck.settled.isoformat(),
                str(recheck.outcome),
                recheck.note,
                recheck.recheck_id,
            ),
        )

    def find(self, recheck_id: int) -> Recheck | None:
        """The request, or None."""
        row = self._connection.execute(
            "SELECT * FROM recheck WHERE id = ?", (recheck_id,)
        ).fetchone()
        return None if row is None else _recheck_from(row)

    def get(self, recheck_id: int) -> Recheck:
        """The request. Raises if the book does not have it."""
        found = self.find(recheck_id)
        if found is None:
            raise NotFoundError("recheck", str(recheck_id))
        return found

    def open_for(self, tag: str) -> Recheck | None:
        """The bale's open request, or None."""
        row = self._connection.execute(
            "SELECT * FROM recheck WHERE tag = ? AND settled IS NULL", (bale_tag(tag),)
        ).fetchone()
        return None if row is None else _recheck_from(row)

    def history_for(self, tag: str) -> tuple[Recheck, ...]:
        """Every request ever made against a bale, oldest first."""
        rows = self._connection.execute(
            "SELECT * FROM recheck WHERE tag = ? ORDER BY requested, id", (bale_tag(tag),)
        ).fetchall()
        return tuple(_recheck_from(row) for row in rows)

    def all_open(self) -> tuple[Recheck, ...]:
        """Every request the office still has, oldest first."""
        rows = self._connection.execute(
            "SELECT * FROM recheck WHERE settled IS NULL ORDER BY requested, id"
        ).fetchall()
        return tuple(_recheck_from(row) for row in rows)

    def settled_between(self, start: date, end: date) -> tuple[Recheck, ...]:
        """Every request answered in a window, oldest answer first."""
        rows = self._connection.execute(
            "SELECT * FROM recheck WHERE settled IS NOT NULL AND settled BETWEEN ? AND ?"
            " ORDER BY settled, id",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return tuple(_recheck_from(row) for row in rows)

    def count(self) -> int:
        """How many requests the book holds."""
        row = self._connection.execute("SELECT count(*) AS n FROM recheck").fetchone()
        return int(row["n"])


def _recheck_from(row: sqlite3.Row) -> Recheck:
    return Recheck(
        tag=str(row["tag"]),
        requested=as_date(row["requested"]),
        reason=RecheckReason(str(row["reason"])),
        requested_by=str(row["requested_by"]),
        settled=as_optional_date(row["settled"]),
        outcome=RecheckOutcome(str(row["outcome"])),
        note=str(row["note"]),
        recheck_id=int(row["id"]),
    )
