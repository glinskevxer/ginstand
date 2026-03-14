"""Reading and writing the producer account ledger."""

from __future__ import annotations

import sqlite3
from datetime import date

from ginstand.errors import NotFoundError
from ginstand.ids import reference
from ginstand.model.account import Entry, EntryKind
from ginstand.store.sqlite import as_date
from ginstand.units.money import Money


class AccountStore:
    """Every entry on every producer's account."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def post(self, entry: Entry) -> Entry:
        """Put an entry on an account and hand it back with its id."""
        cursor = self._connection.execute(
            "INSERT INTO account_entry (producer, crop_year, made, kind, amount, run,"
            " reference, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry.producer,
                entry.crop_year,
                entry.made.isoformat(),
                str(entry.kind),
                int(entry.amount),
                entry.run or None,
                entry.reference,
                entry.note,
            ),
        )
        return self.get(int(cursor.lastrowid or 0))

    def find(self, entry_id: int) -> Entry | None:
        """The entry, or None."""
        row = self._connection.execute(
            "SELECT * FROM account_entry WHERE id = ?", (entry_id,)
        ).fetchone()
        return None if row is None else _entry_from(row)

    def get(self, entry_id: int) -> Entry:
        """The entry. Raises if the book does not have it."""
        found = self.find(entry_id)
        if found is None:
            raise NotFoundError("account entry", str(entry_id))
        return found

    def remove(self, entry_id: int) -> None:
        """Take an entry off an account. Raises if it is not there."""
        self.get(entry_id)
        self._connection.execute("DELETE FROM account_entry WHERE id = ?", (entry_id,))

    def entries(self, producer: str, crop_year: int) -> tuple[Entry, ...]:
        """Every entry on one account, oldest first."""
        rows = self._connection.execute(
            "SELECT * FROM account_entry WHERE producer = ? AND crop_year = ? ORDER BY made, id",
            (reference(producer, "producer"), crop_year),
        ).fetchall()
        return tuple(_entry_from(row) for row in rows)

    def settlement_for(self, producer: str, run: str) -> Entry | None:
        """The settlement entry for one producer on one run, or None."""
        row = self._connection.execute(
            "SELECT * FROM account_entry WHERE producer = ? AND run = ? AND kind = 'settlement'",
            (reference(producer, "producer"), reference(run, "gin run")),
        ).fetchone()
        return None if row is None else _entry_from(row)

    def balance(self, producer: str, crop_year: int) -> Money:
        """What the gin owes a producer, negative where they owe the gin."""
        row = self._connection.execute(
            "SELECT coalesce(sum(amount), 0) AS total FROM account_entry"
            " WHERE producer = ? AND crop_year = ?",
            (reference(producer, "producer"), crop_year),
        ).fetchone()
        return Money(int(row["total"]))

    def totals(self, producer: str, crop_year: int) -> dict[EntryKind, Money]:
        """What each kind of entry adds up to on one account."""
        rows = self._connection.execute(
            "SELECT kind, sum(amount) AS total FROM account_entry"
            " WHERE producer = ? AND crop_year = ? GROUP BY kind",
            (reference(producer, "producer"), crop_year),
        ).fetchall()
        found = {EntryKind(str(row["kind"])): Money(int(row["total"])) for row in rows}
        return {kind: found.get(kind, Money(0)) for kind in EntryKind}

    def producers_with_entries(self, crop_year: int) -> tuple[str, ...]:
        """Every producer with an account in a crop year, in reference order."""
        rows = self._connection.execute(
            "SELECT DISTINCT producer FROM account_entry WHERE crop_year = ? ORDER BY producer",
            (crop_year,),
        ).fetchall()
        return tuple(str(row["producer"]) for row in rows)

    def posted_on(self, day: date) -> tuple[Entry, ...]:
        """Every entry posted on a day, across every account."""
        rows = self._connection.execute(
            "SELECT * FROM account_entry WHERE made = ? ORDER BY producer, id",
            (day.isoformat(),),
        ).fetchall()
        return tuple(_entry_from(row) for row in rows)

    def count(self) -> int:
        """How many entries the ledger holds."""
        row = self._connection.execute("SELECT count(*) AS n FROM account_entry").fetchone()
        return int(row["n"])


def _entry_from(row: sqlite3.Row) -> Entry:
    return Entry(
        producer=str(row["producer"]),
        crop_year=int(row["crop_year"]),
        made=as_date(row["made"]),
        kind=EntryKind(str(row["kind"])),
        amount=Money(int(row["amount"])),
        run=str(row["run"] or ""),
        reference=str(row["reference"]),
        note=str(row["note"]),
        entry_id=int(row["id"]),
    )
