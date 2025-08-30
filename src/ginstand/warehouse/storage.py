"""What the warehouse charges for keeping a bale.

Three numbers and they do not act independently. There is a handling charge on
the way in, a daily rate while the bale sits, and a load out charge when it
leaves. On top of that the contract carries a free period and a minimum period,
and those two are where the arithmetic stops being obvious.

The free period comes off the bill. The minimum period is a floor under the days
charged, not under the bill, so a bale released inside the minimum is charged the
minimum less the free days rather than the days it was actually there. A bale
pulled out after twelve days on a sixty day minimum with ten days free is
charged for fifty days, not for two.

Getting that the wrong way round is worth about forty cents a bale, which is
nothing on a bale and eight hundred dollars on a season's worth.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ginstand.errors import ValidationError
from ginstand.model.warehouse import Receipt
from ginstand.store.book import Book
from ginstand.units.money import Money, format_money


@dataclass(frozen=True, slots=True)
class StorageTariff:
    """A warehouse contract's charges."""

    receiving: Money
    """Charged once, per bale, on the way in."""

    per_day: Money
    """Charged per bale per chargeable day."""

    load_out: Money
    """Charged once, per bale, when the bale leaves."""

    free_days: int = 0
    """Days at the front that are not charged."""

    minimum_days: int = 0
    """The floor under the days charged, before the free days come off."""

    def __post_init__(self) -> None:
        for name in ("receiving", "per_day", "load_out"):
            if getattr(self, name) < 0:
                raise ValidationError(name, "must not be negative")
        if self.free_days < 0 or self.minimum_days < 0:
            raise ValidationError("days", "must not be negative")
        if self.free_days > self.minimum_days and self.minimum_days > 0:
            raise ValidationError(
                "free days",
                f"{self.free_days} free days is more than the {self.minimum_days} "
                f"day minimum, so the minimum can never be charged",
            )

    def chargeable_days(self, days_stored: int) -> int:
        """How many days a stay of ``days_stored`` days is charged for."""
        if days_stored < 0:
            raise ValidationError("days stored", "must not be negative")
        if days_stored <= self.free_days:
            return 0
        return max(days_stored, self.minimum_days) - self.free_days


@dataclass(frozen=True, slots=True)
class StorageBill:
    """What one bale has cost to keep."""

    receipt: str
    tag: str
    days_stored: int
    chargeable_days: int
    receiving: Money
    storage: Money
    load_out: Money

    @property
    def total(self) -> Money:
        """Everything owed on this bale."""
        return Money(self.receiving + self.storage + self.load_out)

    @property
    def line(self) -> str:
        """The line a storage bill prints."""
        return (
            f"{self.receipt}  {self.tag}  {self.days_stored} days "
            f"({self.chargeable_days} charged)  {format_money(self.total)}"
        )


def bill_receipt(tariff: StorageTariff, receipt: Receipt, through: date) -> StorageBill:
    """Bill one receipt up to a day, or to its release if it has one."""
    days = receipt.days_stored(through)
    chargeable = tariff.chargeable_days(days)
    return StorageBill(
        receipt=receipt.number,
        tag=receipt.tag,
        days_stored=days,
        chargeable_days=chargeable,
        receiving=tariff.receiving,
        storage=Money(chargeable * tariff.per_day),
        load_out=tariff.load_out if not receipt.outstanding else Money(0),
    )


def bill_holder(
    book: Book, tariff: StorageTariff, holder: str, through: date
) -> tuple[StorageBill, ...]:
    """Bill every receipt somebody holds, released ones included."""
    return tuple(
        bill_receipt(tariff, receipt, through)
        for receipt in book.receipts.for_holder(holder)
        if receipt.issued <= through
    )


def total_for_holder(book: Book, tariff: StorageTariff, holder: str, through: date) -> Money:
    """What somebody owes the warehouse in total."""
    return Money(sum(bill.total for bill in bill_holder(book, tariff, holder, through)))
