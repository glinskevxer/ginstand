"""Reading and writing farms and fields.

Fields are the join between the grower records and the cotton records. A module
names a field, the field names a farm and a lease, and the lease names who gets
paid. Every settlement in this package walks that chain, so the lookups that
walk it are here rather than assembled at each caller.
"""

from __future__ import annotations

import sqlite3

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.ids import reference
from ginstand.model.farm import Farm, Field
from ginstand.store.sqlite import as_decimal


class FarmStore:
    """The farm register."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, farm: Farm) -> None:
        """Put a farm in the book. Raises if the reference is taken."""
        if self.exists(farm.ref):
            raise DuplicateError("farm", farm.ref)
        self._connection.execute(
            "INSERT INTO farm (ref, producer, name, fsa_number, county) VALUES (?, ?, ?, ?, ?)",
            (farm.ref, farm.producer, farm.name, farm.fsa_number, farm.county),
        )

    def update(self, farm: Farm) -> None:
        """Replace a farm that is already in the book."""
        if not self.exists(farm.ref):
            raise NotFoundError("farm", farm.ref)
        self._connection.execute(
            "UPDATE farm SET producer = ?, name = ?, fsa_number = ?, county = ? WHERE ref = ?",
            (farm.producer, farm.name, farm.fsa_number, farm.county, farm.ref),
        )

    def find(self, ref: str) -> Farm | None:
        """The farm, or None."""
        key = reference(ref, "farm")
        row = self._connection.execute("SELECT * FROM farm WHERE ref = ?", (key,)).fetchone()
        return None if row is None else _farm_from(row)

    def get(self, ref: str) -> Farm:
        """The farm. Raises if the book does not have it."""
        found = self.find(ref)
        if found is None:
            raise NotFoundError("farm", reference(ref, "farm"))
        return found

    def exists(self, ref: str) -> bool:
        """Whether the book has a farm under this reference."""
        return self.find(ref) is not None

    def list_all(self) -> tuple[Farm, ...]:
        """Every farm, in reference order."""
        rows = self._connection.execute("SELECT * FROM farm ORDER BY ref").fetchall()
        return tuple(_farm_from(row) for row in rows)

    def for_producer(self, producer: str) -> tuple[Farm, ...]:
        """Every farm a producer runs."""
        key = reference(producer, "producer")
        rows = self._connection.execute(
            "SELECT * FROM farm WHERE producer = ? ORDER BY ref", (key,)
        ).fetchall()
        return tuple(_farm_from(row) for row in rows)


class FieldStore:
    """The field register."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def add(self, plot: Field) -> None:
        """Put a field in the book. Raises if the reference is taken."""
        if self.exists(plot.ref):
            raise DuplicateError("field", plot.ref)
        self._connection.execute(
            "INSERT INTO field (ref, farm, name, acres, lease, variety, irrigated)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                plot.ref,
                plot.farm,
                plot.name,
                str(plot.acres),
                plot.lease,
                plot.variety,
                int(plot.irrigated),
            ),
        )

    def update(self, plot: Field) -> None:
        """Replace a field that is already in the book."""
        if not self.exists(plot.ref):
            raise NotFoundError("field", plot.ref)
        self._connection.execute(
            "UPDATE field SET farm = ?, name = ?, acres = ?, lease = ?, variety = ?,"
            " irrigated = ? WHERE ref = ?",
            (
                plot.farm,
                plot.name,
                str(plot.acres),
                plot.lease,
                plot.variety,
                int(plot.irrigated),
                plot.ref,
            ),
        )

    def find(self, ref: str) -> Field | None:
        """The field, or None."""
        key = reference(ref, "field")
        row = self._connection.execute("SELECT * FROM field WHERE ref = ?", (key,)).fetchone()
        return None if row is None else _field_from(row)

    def get(self, ref: str) -> Field:
        """The field. Raises if the book does not have it."""
        found = self.find(ref)
        if found is None:
            raise NotFoundError("field", reference(ref, "field"))
        return found

    def exists(self, ref: str) -> bool:
        """Whether the book has a field under this reference."""
        return self.find(ref) is not None

    def list_all(self) -> tuple[Field, ...]:
        """Every field, in reference order."""
        rows = self._connection.execute("SELECT * FROM field ORDER BY ref").fetchall()
        return tuple(_field_from(row) for row in rows)

    def for_farm(self, farm: str) -> tuple[Field, ...]:
        """Every field on a farm."""
        key = reference(farm, "farm")
        rows = self._connection.execute(
            "SELECT * FROM field WHERE farm = ? ORDER BY ref", (key,)
        ).fetchall()
        return tuple(_field_from(row) for row in rows)

    def for_lease(self, lease: str) -> tuple[Field, ...]:
        """Every field farmed under one lease."""
        key = reference(lease, "lease")
        rows = self._connection.execute(
            "SELECT * FROM field WHERE lease = ? ORDER BY ref", (key,)
        ).fetchall()
        return tuple(_field_from(row) for row in rows)


def _farm_from(row: sqlite3.Row) -> Farm:
    return Farm(
        ref=str(row["ref"]),
        producer=str(row["producer"]),
        name=str(row["name"]),
        fsa_number=str(row["fsa_number"]),
        county=str(row["county"]),
    )


def _field_from(row: sqlite3.Row) -> Field:
    return Field(
        ref=str(row["ref"]),
        farm=str(row["farm"]),
        name=str(row["name"]),
        acres=as_decimal(row["acres"]),
        lease=str(row["lease"]),
        variety=str(row["variety"]),
        irrigated=bool(row["irrigated"]),
    )
