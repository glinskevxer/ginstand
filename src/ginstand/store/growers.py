"""Reading and writing producers and the leases they gin under.

Every store in this package follows the same three rules. Adding a record that
is already there raises rather than overwriting, because in an office the second
one is nearly always a duplicate rather than a correction. Updating a record
that is not there raises for the same reason in reverse. And a get that finds
nothing raises, while a find that finds nothing returns None, so a caller says
in its own code which of the two it meant.
"""

from __future__ import annotations

import sqlite3
from decimal import Decimal

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.ids import reference
from ginstand.model.producer import Lease, LeaseKind, Producer
from ginstand.store.repository import Repository
from ginstand.store.sqlite import as_decimal


class ProducerStore(Repository[Producer]):
    """The producer register."""

    table = "producer"
    kind = "producer"

    def _from_row(self, row: sqlite3.Row) -> Producer:
        return _producer_from(row)

    def add(self, producer: Producer) -> None:
        """Put a producer in the book. Raises if the reference is taken."""
        if self.exists(producer.ref):
            raise DuplicateError("producer", producer.ref)
        self._connection.execute(
            "INSERT INTO producer (ref, name, address, phone, ccc_number) VALUES (?, ?, ?, ?, ?)",
            (producer.ref, producer.name, producer.address, producer.phone, producer.ccc_number),
        )

    def update(self, producer: Producer) -> None:
        """Replace a producer that is already in the book."""
        if not self.exists(producer.ref):
            raise NotFoundError("producer", producer.ref)
        self._connection.execute(
            "UPDATE producer SET name = ?, address = ?, phone = ?, ccc_number = ? WHERE ref = ?",
            (producer.name, producer.address, producer.phone, producer.ccc_number, producer.ref),
        )


class LeaseStore(Repository[Lease]):
    """The lease register."""

    table = "lease"
    kind = "lease"

    def _from_row(self, row: sqlite3.Row) -> Lease:
        return _lease_from(row)

    def add(self, lease: Lease) -> None:
        """Put a lease in the book. Raises if the reference is taken."""
        if self.exists(lease.ref):
            raise DuplicateError("lease", lease.ref)
        self._connection.execute(
            "INSERT INTO lease (ref, tenant, kind, landlord, landlord_share)"
            " VALUES (?, ?, ?, ?, ?)",
            (lease.ref, lease.tenant, str(lease.kind), lease.landlord, str(lease.landlord_share)),
        )

    def update(self, lease: Lease) -> None:
        """Replace a lease that is already in the book."""
        if not self.exists(lease.ref):
            raise NotFoundError("lease", lease.ref)
        self._connection.execute(
            "UPDATE lease SET tenant = ?, kind = ?, landlord = ?, landlord_share = ? WHERE ref = ?",
            (lease.tenant, str(lease.kind), lease.landlord, str(lease.landlord_share), lease.ref),
        )

    def for_tenant(self, tenant: str) -> tuple[Lease, ...]:
        """Every lease a producer farms under."""
        return self._select("tenant = ?", (reference(tenant, "tenant"),))


def _producer_from(row: sqlite3.Row) -> Producer:
    return Producer(
        ref=str(row["ref"]),
        name=str(row["name"]),
        address=str(row["address"]),
        phone=str(row["phone"]),
        ccc_number=str(row["ccc_number"]),
    )


def _lease_from(row: sqlite3.Row) -> Lease:
    return Lease(
        ref=str(row["ref"]),
        tenant=str(row["tenant"]),
        kind=LeaseKind(str(row["kind"])),
        landlord=str(row["landlord"]),
        landlord_share=as_decimal(row["landlord_share"]) if row["landlord_share"] else Decimal("0"),
    )
