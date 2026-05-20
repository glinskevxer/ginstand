"""Reading and writing instruments and their calibration log."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.ids import reference
from ginstand.model.instrument import Calibration, Instrument, InstrumentKind
from ginstand.store.repository import Repository
from ginstand.store.sqlite import as_date, as_decimal, as_optional_date


class InstrumentStore(Repository[Instrument]):
    """The instruments the gin's numbers come off."""

    table = "instrument"
    kind = "instrument"

    def _from_row(self, row: sqlite3.Row) -> Instrument:
        return _instrument_from(row)

    def add(self, instrument: Instrument) -> None:
        """Put an instrument in the book."""
        if self.exists(instrument.ref):
            raise DuplicateError("instrument", instrument.ref)
        self._connection.execute(
            "INSERT INTO instrument (ref, kind, description, serial, retired)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                instrument.ref,
                str(instrument.kind),
                instrument.description,
                instrument.serial,
                None if instrument.retired is None else instrument.retired.isoformat(),
            ),
        )

    def save(self, instrument: Instrument) -> None:
        """Replace an instrument that is already in the book."""
        if not self.exists(instrument.ref):
            raise NotFoundError("instrument", instrument.ref)
        self._connection.execute(
            "UPDATE instrument SET kind = ?, description = ?, serial = ?, retired = ?"
            " WHERE ref = ?",
            (
                str(instrument.kind),
                instrument.description,
                instrument.serial,
                None if instrument.retired is None else instrument.retired.isoformat(),
                instrument.ref,
            ),
        )

    def in_service(self) -> tuple[Instrument, ...]:
        """Every instrument still being used."""
        return self._select("retired IS NULL", ())

    def of_kind(self, kind: InstrumentKind) -> tuple[Instrument, ...]:
        """Every instrument of one kind."""
        return self._select("kind = ?", (str(kind),))


class CalibrationStore:
    """Every check ever made against an instrument."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def record(self, calibration: Calibration) -> Calibration:
        """Log a check and hand it back with its id."""
        cursor = self._connection.execute(
            "INSERT INTO calibration (instrument, checked, by_whom, error, passed, note)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                calibration.instrument,
                calibration.checked.isoformat(),
                calibration.by_whom,
                str(calibration.error),
                int(calibration.passed),
                calibration.note,
            ),
        )
        return self.get(int(cursor.lastrowid or 0))

    def find(self, calibration_id: int) -> Calibration | None:
        """The check, or None."""
        row = self._connection.execute(
            "SELECT * FROM calibration WHERE id = ?", (calibration_id,)
        ).fetchone()
        return None if row is None else _calibration_from(row)

    def get(self, calibration_id: int) -> Calibration:
        """The check. Raises if the book does not have it."""
        found = self.find(calibration_id)
        if found is None:
            raise NotFoundError("calibration", str(calibration_id))
        return found

    def history_for(self, instrument: str) -> tuple[Calibration, ...]:
        """Every check against one instrument, oldest first."""
        rows = self._connection.execute(
            "SELECT * FROM calibration WHERE instrument = ? ORDER BY checked, id",
            (reference(instrument, "instrument"),),
        ).fetchall()
        return tuple(_calibration_from(row) for row in rows)

    def last_before(self, instrument: str, day: date) -> Calibration | None:
        """The most recent check on or before a day."""
        row = self._connection.execute(
            "SELECT * FROM calibration WHERE instrument = ? AND checked <= ?"
            " ORDER BY checked DESC, id DESC LIMIT 1",
            (reference(instrument, "instrument"), day.isoformat()),
        ).fetchone()
        return None if row is None else _calibration_from(row)

    def failures(self) -> tuple[Calibration, ...]:
        """Every check that did not pass, oldest first."""
        rows = self._connection.execute(
            "SELECT * FROM calibration WHERE passed = 0 ORDER BY checked, id"
        ).fetchall()
        return tuple(_calibration_from(row) for row in rows)

    def count(self) -> int:
        """How many checks the log holds."""
        row = self._connection.execute("SELECT count(*) AS n FROM calibration").fetchone()
        return int(row["n"])


def _instrument_from(row: sqlite3.Row) -> Instrument:
    return Instrument(
        ref=str(row["ref"]),
        kind=InstrumentKind(str(row["kind"])),
        description=str(row["description"]),
        serial=str(row["serial"]),
        retired=as_optional_date(row["retired"]),
    )


def _calibration_from(row: sqlite3.Row) -> Calibration:
    return Calibration(
        instrument=str(row["instrument"]),
        checked=as_date(row["checked"]),
        error=as_decimal(row["error"]) if row["error"] else Decimal("0"),
        passed=bool(row["passed"]),
        by_whom=str(row["by_whom"]),
        note=str(row["note"]),
        calibration_id=int(row["id"]),
    )
