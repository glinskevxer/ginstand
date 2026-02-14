"""Reading and writing who owns which bale, and the carry between runs.

Two tables, and they answer two different questions. The allocation table says
which producer a bale belongs to, and it is the record the warehouse receipt and
the settlement both work off. The carry table says what each producer was owed
and did not get, and it exists so the next run can put it right.

Carries are per crop year. A fraction of a bale does not survive a season: at
the end of the year it is settled in lint pounds on the last statement and the
next year starts everybody at zero.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Mapping
from datetime import date
from decimal import Decimal

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.ids import bale_tag, reference
from ginstand.store.sqlite import as_decimal


class AllocationStore:
    """Which producer owns each bale, and the fractions carried between runs."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def assign(self, tag: str, producer: str, run: str, on: date) -> None:
        """Give a bale to a producer. Raises if it already has an owner."""
        key = bale_tag(tag)
        owner = self.owner_of(key)
        if owner is not None:
            raise DuplicateError("bale allocation", key)
        self._connection.execute(
            "INSERT INTO bale_allocation (tag, producer, run, allocated) VALUES (?, ?, ?, ?)",
            (key, reference(producer, "producer"), reference(run, "gin run"), on.isoformat()),
        )

    def owner_of(self, tag: str) -> str | None:
        """Which producer owns a bale, or None if it is not allocated yet."""
        row = self._connection.execute(
            "SELECT producer FROM bale_allocation WHERE tag = ?", (bale_tag(tag),)
        ).fetchone()
        return None if row is None else str(row["producer"])

    def require_owner(self, tag: str) -> str:
        """Which producer owns a bale. Raises if it is not allocated."""
        owner = self.owner_of(tag)
        if owner is None:
            raise NotFoundError("bale allocation", bale_tag(tag))
        return owner

    def bales_for(self, producer: str) -> tuple[str, ...]:
        """Every bale a producer owns, in tag order."""
        rows = self._connection.execute(
            "SELECT tag FROM bale_allocation WHERE producer = ? ORDER BY tag",
            (reference(producer, "producer"),),
        ).fetchall()
        return tuple(str(row["tag"]) for row in rows)

    def bales_for_run(self, run: str) -> dict[str, str]:
        """Every allocated bale off a run, tag to producer, in tag order."""
        rows = self._connection.execute(
            "SELECT tag, producer FROM bale_allocation WHERE run = ? ORDER BY tag",
            (reference(run, "gin run"),),
        ).fetchall()
        return {str(row["tag"]): str(row["producer"]) for row in rows}

    def run_is_allocated(self, run: str) -> bool:
        """Whether any bale off this run has been given an owner."""
        return bool(self.bales_for_run(run))

    def counts_for_run(self, run: str) -> dict[str, int]:
        """How many bales off a run each producer got."""
        counts: dict[str, int] = {}
        for producer in self.bales_for_run(run).values():
            counts[producer] = counts.get(producer, 0) + 1
        return counts

    def carry_for(self, producer: str, crop_year: int) -> Decimal:
        """What a producer is owed going into their next run this crop year."""
        row = self._connection.execute(
            "SELECT carry FROM allocation_carry WHERE producer = ? AND crop_year = ?",
            (reference(producer, "producer"), crop_year),
        ).fetchone()
        return Decimal("0") if row is None else as_decimal(row["carry"])

    def set_carry(self, producer: str, crop_year: int, carry: Decimal) -> None:
        """Record what a producer is owed after a run."""
        self._connection.execute(
            "INSERT INTO allocation_carry (producer, crop_year, carry) VALUES (?, ?, ?)"
            " ON CONFLICT (producer, crop_year) DO UPDATE SET carry = excluded.carry",
            (reference(producer, "producer"), crop_year, str(carry)),
        )

    def set_carries(self, carries: Mapping[str, Decimal], crop_year: int) -> None:
        """Record a whole run's worth of carries."""
        for producer, carry in carries.items():
            self.set_carry(producer, crop_year, carry)

    def carries(self, crop_year: int) -> dict[str, Decimal]:
        """Every carry standing in a crop year, in producer order."""
        rows = self._connection.execute(
            "SELECT producer, carry FROM allocation_carry WHERE crop_year = ? ORDER BY producer",
            (crop_year,),
        ).fetchall()
        return {str(row["producer"]): as_decimal(row["carry"]) for row in rows}
