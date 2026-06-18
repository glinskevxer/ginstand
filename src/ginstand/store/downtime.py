"""Reading and writing the downtime log."""

from __future__ import annotations

import sqlite3
from datetime import date

from ginstand.errors import NotFoundError
from ginstand.ids import reference
from ginstand.model.downtime import Stop, StopReason
from ginstand.store.sqlite import as_date


class DowntimeStore:
    """Every stop the gin has written down."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def log(self, stop: Stop) -> Stop:
        """Write a stop down and hand it back with its id."""
        cursor = self._connection.execute(
            "INSERT INTO downtime (run, stopped, started, minutes, reason, note)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                stop.run,
                stop.stopped.isoformat(),
                stop.started,
                stop.minutes,
                str(stop.reason),
                stop.note,
            ),
        )
        return self.get(int(cursor.lastrowid or 0))

    def find(self, stop_id: int) -> Stop | None:
        """The stop, or None."""
        row = self._connection.execute("SELECT * FROM downtime WHERE id = ?", (stop_id,)).fetchone()
        return None if row is None else _stop_from(row)

    def get(self, stop_id: int) -> Stop:
        """The stop. Raises if the book does not have it."""
        found = self.find(stop_id)
        if found is None:
            raise NotFoundError("stop", str(stop_id))
        return found

    def remove(self, stop_id: int) -> None:
        """Take a stop out of the log. Raises if it is not there."""
        self.get(stop_id)
        self._connection.execute("DELETE FROM downtime WHERE id = ?", (stop_id,))

    def for_run(self, run: str) -> tuple[Stop, ...]:
        """Every stop on a run, in the order they happened."""
        rows = self._connection.execute(
            "SELECT * FROM downtime WHERE run = ? ORDER BY stopped, started, id",
            (reference(run, "gin run"),),
        ).fetchall()
        return tuple(_stop_from(row) for row in rows)

    def on_day(self, day: date) -> tuple[Stop, ...]:
        """Every stop on one day, across every run."""
        rows = self._connection.execute(
            "SELECT * FROM downtime WHERE stopped = ? ORDER BY started, id",
            (day.isoformat(),),
        ).fetchall()
        return tuple(_stop_from(row) for row in rows)

    def minutes_for(self, run: str) -> int:
        """Every minute the gin was stopped on a run."""
        row = self._connection.execute(
            "SELECT coalesce(sum(minutes), 0) AS total FROM downtime WHERE run = ?",
            (reference(run, "gin run"),),
        ).fetchone()
        return int(row["total"])

    def minutes_by_reason(self, run: str) -> dict[StopReason, int]:
        """The minutes on a run, split by why the gin stopped."""
        rows = self._connection.execute(
            "SELECT reason, sum(minutes) AS total FROM downtime WHERE run = ?"
            " GROUP BY reason ORDER BY total DESC",
            (reference(run, "gin run"),),
        ).fetchall()
        return {StopReason(str(row["reason"])): int(row["total"]) for row in rows}

    def count(self) -> int:
        """How many stops the log holds."""
        row = self._connection.execute("SELECT count(*) AS n FROM downtime").fetchone()
        return int(row["n"])


def _stop_from(row: sqlite3.Row) -> Stop:
    return Stop(
        run=str(row["run"]),
        stopped=as_date(row["stopped"]),
        started=int(row["started"]),
        minutes=int(row["minutes"]),
        reason=StopReason(str(row["reason"])),
        note=str(row["note"]),
        stop_id=int(row["id"]),
    )
