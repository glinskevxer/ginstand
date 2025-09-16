"""Splitting a settlement between a tenant and a landlord.

Two rules, and both of them are about the split being arguable rather than about
it being convenient.

The split runs on the settlement total, not on the lint value. A landlord on a
quarter share is entitled to a quarter of the crop and carries a quarter of the
cost of turning it into a saleable bale, so a ginning charge moves their share.
Splitting the lint and then charging the tenant for all the ginning is a
different deal, and it is not the deal the lease describes.

The two parts add back to the whole exactly. That is arranged rather than hoped
for: one side is rounded and the other is the remainder. Rounding both
independently leaves a cent adrift about half the time, and a cent adrift on a
statement is a phone call.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ginstand.errors import ValidationError
from ginstand.model.producer import Lease
from ginstand.units.money import Money, format_money, share_of


@dataclass(frozen=True, slots=True)
class LeaseSplit:
    """A settlement total divided between the parties to a lease."""

    lease: str
    total: Money
    tenant: str
    tenant_amount: Money
    landlord: str
    landlord_amount: Money
    landlord_share: Decimal

    def __post_init__(self) -> None:
        if self.tenant_amount + self.landlord_amount != self.total:
            raise ValidationError(
                "split",
                f"{format_money(self.tenant_amount)} and "
                f"{format_money(self.landlord_amount)} do not add back to "
                f"{format_money(self.total)}",
            )

    @property
    def splits(self) -> bool:
        """Whether there are two parties on this settlement."""
        return bool(self.landlord)

    @property
    def lines(self) -> tuple[str, ...]:
        """The split as a statement prints it."""
        if not self.splits:
            return (f"{self.tenant:<8} {format_money(self.tenant_amount):>12}",)
        return (
            f"{self.tenant:<8} {format_money(self.tenant_amount):>12}",
            f"{self.landlord:<8} {format_money(self.landlord_amount):>12}"
            f"  ({self.landlord_share} share)",
        )


def split_settlement(total: Money, lease: Lease) -> LeaseSplit:
    """Divide a settlement total under a lease.

    The landlord's part is the rounded one and the tenant takes the remainder.
    That choice is arbitrary and it is fixed here so the same lot splits the same
    way every time it is worked out.
    """
    if not lease.splits:
        return LeaseSplit(
            lease=lease.ref,
            total=total,
            tenant=lease.tenant,
            tenant_amount=total,
            landlord="",
            landlord_amount=Money(0),
            landlord_share=Decimal("0"),
        )
    landlord_amount = _rounded_share(total, lease.landlord_share)
    return LeaseSplit(
        lease=lease.ref,
        total=total,
        tenant=lease.tenant,
        tenant_amount=Money(total - landlord_amount),
        landlord=lease.landlord,
        landlord_amount=landlord_amount,
        landlord_share=lease.landlord_share,
    )


def _rounded_share(total: Money, fraction: Decimal) -> Money:
    if total < 0:
        return Money(-share_of(Money(-total), fraction))
    return share_of(total, fraction)
