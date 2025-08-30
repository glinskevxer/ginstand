"""Reading and writing warehouses and receipts.

The unique index on the receipt's bale tag is what stops a bale being receipted
twice while the first receipt is outstanding. It is a plain unique index rather
than a partial one, which means a released bale keeps its old receipt and a new
one needs the old row moved aside first. That is deliberate: a bale coming back
into store is rare enough to be worth a person looking at it.
"""

from __future__ import annotations

import sqlite3
from datetime import date

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.ids import parse_pbi, reference
from ginstand.model.warehouse import Receipt, Warehouse
from ginstand.store.repository import Repository
from ginstand.store.sqlite import as_date, as_optional_date


class WarehouseStore(Repository[Warehouse]):
    """The warehouses the gin ships to."""

    table = "warehouse"
    kind = "warehouse"

    def _from_row(self, row: sqlite3.Row) -> Warehouse:
        return _warehouse_from(row)

    def add(self, house: Warehouse) -> None:
        """Put a warehouse in the book."""
        if self.exists(house.ref):
            raise DuplicateError("warehouse", house.ref)
        self._connection.execute(
            "INSERT INTO warehouse (ref, name, code, location) VALUES (?, ?, ?, ?)",
            (house.ref, house.name, house.code, house.location),
        )

    def update(self, house: Warehouse) -> None:
        """Replace a warehouse that is already in the book."""
        if not self.exists(house.ref):
            raise NotFoundError("warehouse", house.ref)
        self._connection.execute(
            "UPDATE warehouse SET name = ?, code = ?, location = ? WHERE ref = ?",
            (house.name, house.code, house.location, house.ref),
        )

    def licensed(self) -> tuple[Warehouse, ...]:
        """Every warehouse that can issue a receipt a lender will take."""
        return self._select("code <> ''", ())


class ReceiptStore(Repository[Receipt]):
    """Every receipt the gin has had issued against its bales."""

    table = "receipt"
    kind = "receipt"
    key_column = "number"
    order_by = "number"

    def _key(self, value: str) -> str:
        return reference(value, "receipt number")

    def _from_row(self, row: sqlite3.Row) -> Receipt:
        return _receipt_from(row)

    def add(self, receipt: Receipt) -> None:
        """Record a receipt. Raises if the number is taken."""
        if self.exists(receipt.number):
            raise DuplicateError("receipt", receipt.number)
        self._connection.execute(
            "INSERT INTO receipt (number, tag, warehouse, holder, issued, released, note)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                receipt.number,
                receipt.tag,
                receipt.warehouse,
                receipt.holder,
                receipt.issued.isoformat(),
                None if receipt.released is None else receipt.released.isoformat(),
                receipt.note,
            ),
        )

    def save(self, receipt: Receipt) -> None:
        """Replace a receipt that is already in the book."""
        if not self.exists(receipt.number):
            raise NotFoundError("receipt", receipt.number)
        self._connection.execute(
            "UPDATE receipt SET tag = ?, warehouse = ?, holder = ?, issued = ?,"
            " released = ?, note = ? WHERE number = ?",
            (
                receipt.tag,
                receipt.warehouse,
                receipt.holder,
                receipt.issued.isoformat(),
                None if receipt.released is None else receipt.released.isoformat(),
                receipt.note,
                receipt.number,
            ),
        )

    def for_bale(self, tag: str) -> Receipt | None:
        """The receipt against a bale, or None."""
        parse_pbi(tag)
        key = tag.strip().replace(" ", "").replace("-", "")
        row = self._connection.execute("SELECT * FROM receipt WHERE tag = ?", (key,)).fetchone()
        return None if row is None else _receipt_from(row)

    def for_holder(self, holder: str) -> tuple[Receipt, ...]:
        """Every receipt somebody holds, released ones included."""
        return self._select("holder = ?", (reference(holder, "holder"),))

    def outstanding(self) -> tuple[Receipt, ...]:
        """Every receipt still against a bale in store."""
        return self._select("released IS NULL", ())

    def outstanding_for(self, holder: str) -> tuple[Receipt, ...]:
        """Every outstanding receipt somebody holds."""
        return self._select("holder = ? AND released IS NULL", (reference(holder, "holder"),))

    def in_warehouse(self, warehouse: str) -> tuple[Receipt, ...]:
        """Every outstanding receipt at one warehouse."""
        return self._select(
            "warehouse = ? AND released IS NULL", (reference(warehouse, "warehouse"),)
        )

    def issued_on(self, day: date) -> tuple[Receipt, ...]:
        """Every receipt issued on a day."""
        return self._select("issued = ?", (day.isoformat(),))


def _warehouse_from(row: sqlite3.Row) -> Warehouse:
    return Warehouse(
        ref=str(row["ref"]),
        name=str(row["name"]),
        code=str(row["code"]),
        location=str(row["location"]),
    )


def _receipt_from(row: sqlite3.Row) -> Receipt:
    return Receipt(
        number=str(row["number"]),
        tag=str(row["tag"]),
        warehouse=str(row["warehouse"]),
        holder=str(row["holder"]),
        issued=as_date(row["issued"]),
        released=as_optional_date(row["released"]),
        note=str(row["note"]),
    )
