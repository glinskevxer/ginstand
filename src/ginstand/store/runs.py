"""Reading and writing gin runs, and what was fed into them.

The store keeps two facts about feeding that the database is the right place to
hold: a module goes into at most one run ever, and the positions within a run
are a gapless sequence. Whether the run was open when the module went in is a
rule about how the gin works rather than a fact about the book, and it lives in
the ginning layer with the rest of them.
"""

from __future__ import annotations

import sqlite3
from datetime import date

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.ids import reference
from ginstand.model.ginrun import GinRun
from ginstand.store.sqlite import as_date, as_optional_date


class RunStore:
    """The gin runs, and the modules fed into each one."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, run: GinRun) -> None:
        """Open a run in the book. Raises if the reference is taken."""
        if self.exists(run.ref):
            raise DuplicateError("gin run", run.ref)
        self._connection.execute(
            "INSERT INTO gin_run (ref, crop_year, gin_code, opened, closed, shift, note)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                run.ref,
                run.crop_year,
                run.gin_code,
                run.opened.isoformat(),
                None if run.closed is None else run.closed.isoformat(),
                run.shift,
                run.note,
            ),
        )

    def save(self, run: GinRun) -> None:
        """Replace a run that is already in the book."""
        if not self.exists(run.ref):
            raise NotFoundError("gin run", run.ref)
        self._connection.execute(
            "UPDATE gin_run SET crop_year = ?, gin_code = ?, opened = ?, closed = ?,"
            " shift = ?, note = ? WHERE ref = ?",
            (
                run.crop_year,
                run.gin_code,
                run.opened.isoformat(),
                None if run.closed is None else run.closed.isoformat(),
                run.shift,
                run.note,
                run.ref,
            ),
        )

    def find(self, ref: str) -> GinRun | None:
        """The run, or None."""
        key = reference(ref, "gin run")
        row = self._connection.execute("SELECT * FROM gin_run WHERE ref = ?", (key,)).fetchone()
        return None if row is None else _run_from(row)

    def get(self, ref: str) -> GinRun:
        """The run. Raises if the book does not have it."""
        found = self.find(ref)
        if found is None:
            raise NotFoundError("gin run", reference(ref, "gin run"))
        return found

    def exists(self, ref: str) -> bool:
        """Whether the book has a run under this reference."""
        return self.find(ref) is not None

    def list_all(self) -> tuple[GinRun, ...]:
        """Every run, oldest opened first."""
        rows = self._connection.execute("SELECT * FROM gin_run ORDER BY opened, ref").fetchall()
        return tuple(_run_from(row) for row in rows)

    def for_crop_year(self, crop_year: int) -> tuple[GinRun, ...]:
        """Every run in one crop year."""
        rows = self._connection.execute(
            "SELECT * FROM gin_run WHERE crop_year = ? ORDER BY opened, ref", (crop_year,)
        ).fetchall()
        return tuple(_run_from(row) for row in rows)

    def open_runs(self) -> tuple[GinRun, ...]:
        """Every run that has not been closed."""
        rows = self._connection.execute(
            "SELECT * FROM gin_run WHERE closed IS NULL ORDER BY opened, ref"
        ).fetchall()
        return tuple(_run_from(row) for row in rows)

    def next_position(self, run: str) -> int:
        """The position the next module fed into this run will take."""
        key = reference(run, "gin run")
        row = self._connection.execute(
            "SELECT coalesce(max(position), 0) AS last FROM run_module WHERE run = ?", (key,)
        ).fetchone()
        return int(row["last"]) + 1

    def feed(self, run: str, module: str, fed_on: date) -> int:
        """Put a module into a run and return the position it took."""
        run_key = reference(run, "gin run")
        module_key = reference(module, "module tag")
        if not self.exists(run_key):
            raise NotFoundError("gin run", run_key)
        if self.run_of(module_key) is not None:
            raise DuplicateError("module", module_key)
        position = self.next_position(run_key)
        self._connection.execute(
            "INSERT INTO run_module (run, module, position, fed_on) VALUES (?, ?, ?, ?)",
            (run_key, module_key, position, fed_on.isoformat()),
        )
        return position

    def run_of(self, module: str) -> str | None:
        """Which run a module went into, or None if it is still in the yard."""
        key = reference(module, "module tag")
        row = self._connection.execute(
            "SELECT run FROM run_module WHERE module = ?", (key,)
        ).fetchone()
        return None if row is None else str(row["run"])

    def modules_in(self, run: str) -> tuple[str, ...]:
        """The module tags fed into a run, in the order they went in."""
        key = reference(run, "gin run")
        rows = self._connection.execute(
            "SELECT module FROM run_module WHERE run = ? ORDER BY position", (key,)
        ).fetchall()
        return tuple(str(row["module"]) for row in rows)

    def seed_cotton_in(self, run: str) -> int:
        """Pounds of seed cotton fed into a run."""
        key = reference(run, "gin run")
        row = self._connection.execute(
            "SELECT coalesce(sum(m.gross_pounds - m.tare_pounds), 0) AS net"
            " FROM run_module r JOIN module m ON m.tag = r.module WHERE r.run = ?",
            (key,),
        ).fetchone()
        return int(row["net"])


def _run_from(row: sqlite3.Row) -> GinRun:
    return GinRun(
        ref=str(row["ref"]),
        crop_year=int(row["crop_year"]),
        gin_code=str(row["gin_code"]),
        opened=as_date(row["opened"]),
        closed=as_optional_date(row["closed"]),
        shift=str(row["shift"]),
        note=str(row["note"]),
    )
