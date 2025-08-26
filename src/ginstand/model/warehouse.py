"""Warehouses, and the receipts they issue against bales.

A receipt is a document of title. Whoever holds it owns the bale, and the bale
does not move without it. That is why the receipt names a holder separately from
the producer the bale was allocated to: a producer who sells a lot transfers the
receipts, and the gin's allocation record does not change when they do.

One receipt per bale, ever. A bale that is released and stored again gets a new
receipt with a new number, and the old one is kept showing when it was released.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ginstand.errors import ValidationError
from ginstand.ids import parse_pbi, reference


@dataclass(frozen=True, slots=True)
class Warehouse:
    """Somewhere bales are stored."""

    ref: str
    name: str
    code: str = ""
    """The warehouse code the receipt carries. Blank if it is not licensed."""

    location: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "ref", reference(self.ref, "warehouse"))
        cleaned = self.name.strip()
        if not cleaned:
            raise ValidationError("warehouse name", "is empty")
        object.__setattr__(self, "name", cleaned)
        object.__setattr__(self, "code", self.code.strip().upper())
        object.__setattr__(self, "location", self.location.strip())

    @property
    def licensed(self) -> bool:
        """Whether this warehouse can issue a receipt that a lender will take."""
        return bool(self.code)


@dataclass(frozen=True, slots=True)
class Receipt:
    """One warehouse receipt, outstanding or released."""

    number: str
    tag: str
    warehouse: str
    holder: str
    issued: date
    released: date | None = None
    note: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "number", reference(self.number, "receipt number"))
        parse_pbi(self.tag)
        object.__setattr__(self, "tag", self.tag.strip().replace(" ", "").replace("-", ""))
        object.__setattr__(self, "warehouse", reference(self.warehouse, "warehouse"))
        object.__setattr__(self, "holder", reference(self.holder, "holder"))
        if self.released is not None and self.released < self.issued:
            raise ValidationError(
                "released",
                f"{self.released.isoformat()} is before the receipt was issued "
                f"on {self.issued.isoformat()}",
            )
        object.__setattr__(self, "note", self.note.strip())

    @property
    def outstanding(self) -> bool:
        """Whether the bale is still under this receipt."""
        return self.released is None

    def days_stored(self, through: date) -> int:
        """Days the bale has been in store, counting to ``through`` if still there."""
        end = self.released if self.released is not None else through
        if end < self.issued:
            raise ValidationError("through", f"{end.isoformat()} is before the receipt was issued")
        return (end - self.issued).days

    def release_on(self, day: date) -> Receipt:
        """The same receipt, released."""
        if self.released is not None:
            raise ValidationError(
                "released", f"receipt {self.number} was released on {self.released.isoformat()}"
            )
        return Receipt(
            number=self.number,
            tag=self.tag,
            warehouse=self.warehouse,
            holder=self.holder,
            issued=self.issued,
            released=day,
            note=self.note,
        )

    def transfer_to(self, holder: str) -> Receipt:
        """The same receipt in somebody else's hands."""
        if self.released is not None:
            raise ValidationError("released", f"receipt {self.number} has been released")
        return Receipt(
            number=self.number,
            tag=self.tag,
            warehouse=self.warehouse,
            holder=holder,
            issued=self.issued,
            released=None,
            note=self.note,
        )
