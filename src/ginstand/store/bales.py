"""Reading and writing bales.

A bale is written when the press releases it and is never changed. The only
thing that happens to it afterwards is that other records start pointing at it:
a classing card, a warehouse receipt, a producer's share of a run.

The sequence lookup is here because the press needs the next number in the crop
year, and that number has to come from the book rather than from a counter the
office keeps on paper.
"""

from __future__ import annotations

import sqlite3
from datetime import date

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.ids import gin_code, parse_pbi, reference
from ginstand.model.bale import Bale
from ginstand.store.sqlite import as_date, as_decimal


class BaleStore:
    """Every bale the gin has pressed."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, bale: Bale) -> None:
        """Record a bale off the press. Raises if the tag is taken."""
        if self.exists(bale.tag):
            raise DuplicateError("bale", bale.tag)
        self._connection.execute(
            "INSERT INTO bale (tag, run, pressed, gross_pounds, tare_pounds, moisture_pct,"
            " stand) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                bale.tag,
                bale.run,
                bale.pressed.isoformat(),
                bale.gross_pounds,
                bale.tare_pounds,
                str(bale.moisture_pct),
                bale.stand,
            ),
        )

    def find(self, tag: str) -> Bale | None:
        """The bale, or None."""
        key = _tag(tag)
        row = self._connection.execute("SELECT * FROM bale WHERE tag = ?", (key,)).fetchone()
        return None if row is None else _bale_from(row)

    def get(self, tag: str) -> Bale:
        """The bale. Raises if the book does not have it."""
        found = self.find(tag)
        if found is None:
            raise NotFoundError("bale", _tag(tag))
        return found

    def exists(self, tag: str) -> bool:
        """Whether the book has a bale under this tag."""
        return self.find(tag) is not None

    def list_all(self) -> tuple[Bale, ...]:
        """Every bale, in tag order, which is crop year then sequence."""
        rows = self._connection.execute("SELECT * FROM bale ORDER BY tag").fetchall()
        return tuple(_bale_from(row) for row in rows)

    def for_run(self, run: str) -> tuple[Bale, ...]:
        """Every bale that came off one run."""
        key = reference(run, "gin run")
        rows = self._connection.execute(
            "SELECT * FROM bale WHERE run = ? ORDER BY tag", (key,)
        ).fetchall()
        return tuple(_bale_from(row) for row in rows)

    def pressed_on(self, day: date) -> tuple[Bale, ...]:
        """Every bale pressed on one day."""
        rows = self._connection.execute(
            "SELECT * FROM bale WHERE pressed = ? ORDER BY tag", (day.isoformat(),)
        ).fetchall()
        return tuple(_bale_from(row) for row in rows)

    def count_for_run(self, run: str) -> int:
        """How many bales came off one run."""
        key = reference(run, "gin run")
        row = self._connection.execute(
            "SELECT count(*) AS n FROM bale WHERE run = ?", (key,)
        ).fetchone()
        return int(row["n"])

    def lint_pounds_for_run(self, run: str) -> int:
        """Net lint off one run, which is the numerator of its turnout."""
        key = reference(run, "gin run")
        row = self._connection.execute(
            "SELECT coalesce(sum(gross_pounds - tare_pounds), 0) AS net FROM bale WHERE run = ?",
            (key,),
        ).fetchone()
        return int(row["net"])

    def last_sequence(self, crop_year: int, code: str) -> int:
        """The highest bale number issued in a crop year. Zero if none yet."""
        prefix = f"{crop_year % 100:02d}{gin_code(code)}"
        row = self._connection.execute(
            "SELECT max(substr(tag, 8)) AS last FROM bale WHERE tag LIKE ? || '%'", (prefix,)
        ).fetchone()
        return 0 if row["last"] is None else int(row["last"])


def _tag(value: str) -> str:
    parse_pbi(value)
    return value.strip().replace(" ", "").replace("-", "")


def _bale_from(row: sqlite3.Row) -> Bale:
    return Bale(
        tag=str(row["tag"]),
        run=str(row["run"]),
        pressed=as_date(row["pressed"]),
        gross_pounds=int(row["gross_pounds"]),
        tare_pounds=int(row["tare_pounds"]),
        moisture_pct=as_decimal(row["moisture_pct"]),
        stand=str(row["stand"]),
    )
