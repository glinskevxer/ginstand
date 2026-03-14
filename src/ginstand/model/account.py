"""The producer account: everything that moves money between gin and grower.

A settlement is worked out from a run and it is also a thing that happened on a
date, which somebody has to be able to look up next March. So it is recorded as
an entry rather than only computed, and adjustments and payments are entries
beside it. The account balance is then one sum over one table instead of a walk
back through every run.

Signs are from the producer's side throughout. A settlement they are owed is
positive, a payment the gin makes is negative, and an adjustment can be either.
A balance above zero is money the gin still owes.

A run can be settled to a producer once. That is the schema's rule rather than
this module's, because two settlements for one run on one account is the sort of
thing that happens when a statement is reprinted and the office is interrupted.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from ginstand.errors import ValidationError
from ginstand.ids import reference
from ginstand.season import check_crop_year
from ginstand.units.money import Money, format_money


class EntryKind(StrEnum):
    """What an entry on the account is."""

    SETTLEMENT = "settlement"
    """What a run came to for this producer."""

    ADJUSTMENT = "adjustment"
    """A correction after the fact: a weight found wrong, a charge missed."""

    PAYMENT = "payment"
    """Money that actually moved."""


@dataclass(frozen=True, slots=True)
class Entry:
    """One line of a producer's account."""

    producer: str
    crop_year: int
    made: date
    kind: EntryKind
    amount: Money
    run: str = ""
    reference: str = ""
    note: str = ""
    entry_id: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "producer", reference(self.producer, "producer"))
        check_crop_year(self.crop_year)
        if self.amount == 0:
            raise ValidationError("amount", f"a {self.kind} of nothing is not an entry")
        if self.kind is EntryKind.SETTLEMENT and not self.run.strip():
            raise ValidationError("run", "a settlement entry names the run it settles")
        if self.kind is EntryKind.PAYMENT and self.amount > 0:
            raise ValidationError(
                "amount",
                f"a payment moves money to the producer, so it is negative, "
                f"got {format_money(self.amount)}",
            )
        object.__setattr__(self, "run", reference(self.run, "gin run") if self.run.strip() else "")
        object.__setattr__(self, "reference", self.reference.strip())
        object.__setattr__(self, "note", self.note.strip())

    @property
    def owed_to_producer(self) -> bool:
        """Whether this entry moves the balance the producer's way."""
        return self.amount > 0

    @property
    def line(self) -> str:
        """The line the account prints."""
        what = self.run or self.reference or "-"
        return (
            f"{self.made.isoformat()}  {self.kind:<10} {what:<12} {format_money(self.amount):>12}"
        )
