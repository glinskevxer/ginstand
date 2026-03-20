"""The file the gin sends the warehouse so it can issue electronic receipts.

Fixed width, like everything else that moves between a gin and somebody else's
system. One record per bale, and a header and a trailer so the warehouse can
tell a truncated file from a short one: the trailer carries the record count and
the total weight, and a file whose trailer disagrees with its body is refused at
the other end rather than half loaded.

The gin's own receipt number goes in the record. The warehouse issues its own
and sends it back, and the two are matched on the bale tag.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ginstand.errors import StateError, ValidationError
from ginstand.ids import bale_tag
from ginstand.store.book import Book

HEADER = "H"
DETAIL = "D"
TRAILER = "T"
RECORD_WIDTH = 60


@dataclass(frozen=True, slots=True)
class Line:
    """One detail record: a bale going into store."""

    tag: str
    net_pounds: int
    gin_code: str
    pressed: date
    holder: str
    receipt: str

    @property
    def text(self) -> str:
        """The record as it goes in the file."""
        return (
            f"{DETAIL}"
            f"{self.tag}"
            f"{self.net_pounds:05d}"
            f"{self.gin_code}"
            f"{self.pressed.strftime('%Y%m%d')}"
            f"{self.holder:<12}"
            f"{self.receipt:<12}"
        ).ljust(RECORD_WIDTH)


def parse_detail(text: str) -> Line:
    """Read one detail record back."""
    if len(text) < RECORD_WIDTH or text[0] != DETAIL:
        raise ValidationError("record", f"is not a detail record: {text[:8]!r}")
    return Line(
        tag=bale_tag(text[1:13]),
        net_pounds=int(text[13:18]),
        gin_code=text[18:23],
        pressed=date(int(text[23:27]), int(text[27:29]), int(text[29:31])),
        holder=text[31:43].strip(),
        receipt=text[43:55].strip(),
    )


def lines_for(book: Book, warehouse: str, on: date) -> tuple[Line, ...]:
    """A detail record for every bale in store at one warehouse."""
    house = book.warehouses.get(warehouse)
    if not house.licensed:
        raise StateError(f"warehouse {house.ref} has no licensed code, so it cannot issue receipts")
    found = []
    for receipt in book.receipts.in_warehouse(house.ref):
        if receipt.issued > on:
            continue
        bale = book.bales.get(receipt.tag)
        run = book.runs.get(bale.run)
        found.append(
            Line(
                tag=bale.tag,
                net_pounds=bale.net_pounds,
                gin_code=run.gin_code,
                pressed=bale.pressed,
                holder=receipt.holder,
                receipt=receipt.number,
            )
        )
    return tuple(found)


def build(book: Book, warehouse: str, on: date) -> tuple[str, ...]:
    """The whole file: header, details, trailer."""
    house = book.warehouses.get(warehouse)
    details = lines_for(book, house.ref, on)
    header = (f"{HEADER}{house.code:<12}{on.strftime('%Y%m%d')}").ljust(RECORD_WIDTH)
    trailer = (f"{TRAILER}{len(details):05d}{sum(item.net_pounds for item in details):09d}").ljust(
        RECORD_WIDTH
    )
    return (header, *(item.text for item in details), trailer)


def check(text: str) -> tuple[Line, ...]:
    """Read a file back and refuse one whose trailer disagrees with its body."""
    rows = [line for line in text.splitlines() if line.strip()]
    if len(rows) < 2 or rows[0][0] != HEADER or rows[-1][0] != TRAILER:
        raise ValidationError("file", "has no header and trailer around it")
    details = tuple(parse_detail(line) for line in rows[1:-1])
    counted = int(rows[-1][1:6])
    weighed = int(rows[-1][6:15])
    if counted != len(details):
        raise ValidationError(
            "trailer", f"says {counted} records and the file carries {len(details)}"
        )
    total = sum(item.net_pounds for item in details)
    if weighed != total:
        raise ValidationError("trailer", f"says {weighed} lb and the records add to {total} lb")
    return details
