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
from ginstand.store.repository import Repository
from ginstand.store.sqlite import as_decimal


class FarmStore(Repository[Farm]):
    """The farm register."""

    table = "farm"
    kind = "farm"

    def _from_row(self, row: sqlite3.Row) -> Farm:
        return _farm_from(row)

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

    def for_producer(self, producer: str) -> tuple[Farm, ...]:
        """Every farm a producer runs."""
        return self._select("producer = ?", (reference(producer, "producer"),))


class FieldStore(Repository[Field]):
    """The field register."""

    table = "field"
    kind = "field"

    def _from_row(self, row: sqlite3.Row) -> Field:
        return _field_from(row)

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

    def for_farm(self, farm: str) -> tuple[Field, ...]:
        """Every field on a farm."""
        return self._select("farm = ?", (reference(farm, "farm"),))

    def for_lease(self, lease: str) -> tuple[Field, ...]:
        """Every field farmed under one lease."""
        return self._select("lease = ?", (reference(lease, "lease"),))


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
