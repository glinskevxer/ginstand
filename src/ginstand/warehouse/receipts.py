"""Issuing, transferring and releasing warehouse receipts.

Four things have to hold before a bale can be receipted, and the order they are
checked in is the order they cost money to get wrong. The bale has to exist. It
has to have been allocated, because a receipt names a holder and nobody knows
who that is until the run is split. It has to be dry enough to store, because a
warehouse that takes a wet bale sends the gin the bill for the ones next to it.
And it must not already be in store.

The receipt number is issued from the book's own sequence rather than typed.
Warehouse receipt numbers get quoted in loan paperwork and a repeated one is
found months later by somebody who is not at this gin.
"""

from __future__ import annotations

from datetime import date

from ginstand.errors import NotFoundError, StateError
from ginstand.ids import reference
from ginstand.model.warehouse import Receipt
from ginstand.store.book import Book

NUMBER_PREFIX = "WR"


def next_number(book: Book) -> str:
    """The number the next receipt will carry."""
    row = book.connection.execute(
        "SELECT max(CAST(substr(number, ?) AS INTEGER)) AS last FROM receipt"
        " WHERE number LIKE ? || '-%'",
        (len(NUMBER_PREFIX) + 2, NUMBER_PREFIX),
    ).fetchone()
    return f"{NUMBER_PREFIX}-{int(row['last'] or 0) + 1:05d}"


def issue(
    book: Book,
    tag: str,
    warehouse: str,
    on: date,
    holder: str = "",
    note: str = "",
) -> Receipt:
    """Put a bale into store and issue the receipt against it."""
    bale = book.bales.get(tag)
    owner = book.allocations.owner_of(bale.tag)
    if owner is None:
        raise StateError(
            f"bale {bale.tag} has not been allocated, so there is nobody to hold a receipt"
        )
    if not bale.storable:
        raise StateError(
            f"bale {bale.tag} was pressed at {bale.moisture_pct}% and is too wet to store"
        )
    standing = book.receipts.for_bale(bale.tag)
    if standing is not None and standing.outstanding:
        raise StateError(f"bale {bale.tag} is already in store under receipt {standing.number}")
    if on < bale.pressed:
        raise StateError(
            f"{on.isoformat()} is before bale {bale.tag} was pressed on {bale.pressed.isoformat()}"
        )
    house = book.warehouses.get(warehouse)
    receipt = Receipt(
        number=next_number(book),
        tag=bale.tag,
        warehouse=house.ref,
        holder=reference(holder, "holder") if holder else owner,
        issued=on,
        note=note,
    )
    book.receipts.add(receipt)
    return receipt


def release(book: Book, number: str, on: date) -> Receipt:
    """Take a bale back out of store."""
    receipt = book.receipts.get(number)
    if not receipt.outstanding:
        raise StateError(f"receipt {receipt.number} was released on {receipt.released}")
    released = receipt.release_on(on)
    book.receipts.save(released)
    return released


def transfer(book: Book, number: str, to_holder: str) -> Receipt:
    """Move a receipt into somebody else's hands."""
    receipt = book.receipts.get(number)
    if not receipt.outstanding:
        raise StateError(f"receipt {receipt.number} has been released")
    holder = book.producers.get(to_holder)
    moved = receipt.transfer_to(holder.ref)
    book.receipts.save(moved)
    return moved


def receipt_for(book: Book, tag: str) -> Receipt:
    """The receipt against a bale. Raises if it is not in store."""
    found = book.receipts.for_bale(tag)
    if found is None:
        raise NotFoundError("receipt", book.bales.get(tag).tag)
    return found


def in_store(book: Book, holder: str) -> tuple[str, ...]:
    """Every bale tag somebody has in store."""
    return tuple(receipt.tag for receipt in book.receipts.outstanding_for(holder))
