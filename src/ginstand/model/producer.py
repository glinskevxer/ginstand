"""Producers, and the lease each one gins under.

The gin pays whoever owns the cotton. On a share lease that is two people, and
the split is on the settlement total rather than on the lint, because a ginning
charge is a cost of turning the crop into something saleable and the landlord
carries their part of it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from ginstand.errors import ValidationError
from ginstand.ids import reference


class LeaseKind(StrEnum):
    """How the cotton off a field is divided before the gin pays for it."""

    OWNER = "owner"
    """The producer farms their own ground. Nothing is split."""

    SHARE = "share"
    """The landlord takes a fraction of the settlement. A quarter is usual."""

    CASH = "cash"
    """The landlord is paid rent in cash and takes none of the crop."""


@dataclass(frozen=True, slots=True)
class Producer:
    """Somebody the gin gins for and settles with."""

    ref: str
    name: str
    address: str = ""
    phone: str = ""
    ccc_number: str = ""
    """The farm number the loan paperwork is filed under. Blank if not enrolled."""

    def __post_init__(self) -> None:
        object.__setattr__(self, "ref", reference(self.ref, "producer"))
        cleaned = self.name.strip()
        if not cleaned:
            raise ValidationError("producer name", "is empty")
        object.__setattr__(self, "name", cleaned)
        object.__setattr__(self, "address", self.address.strip())
        object.__setattr__(self, "phone", self.phone.strip())
        object.__setattr__(self, "ccc_number", self.ccc_number.strip().upper())

    @property
    def enrolled_for_loan(self) -> bool:
        """Whether this producer can put a bale in the CCC loan."""
        return bool(self.ccc_number)


@dataclass(frozen=True, slots=True)
class Lease:
    """The agreement a field is farmed under, and who splits the settlement."""

    ref: str
    tenant: str
    kind: LeaseKind
    landlord: str = ""
    landlord_share: Decimal = field(default=Decimal("0"))

    def __post_init__(self) -> None:
        object.__setattr__(self, "ref", reference(self.ref, "lease"))
        object.__setattr__(self, "tenant", reference(self.tenant, "tenant"))
        share = Decimal(self.landlord_share)
        if self.kind is LeaseKind.SHARE:
            if not self.landlord.strip():
                raise ValidationError("landlord", "a share lease needs a landlord")
            if share <= 0 or share >= 1:
                raise ValidationError(
                    "landlord share", f"must be above 0 and below 1 on a share lease, got {share}"
                )
            object.__setattr__(self, "landlord", reference(self.landlord, "landlord"))
        else:
            if share != 0:
                raise ValidationError(
                    "landlord share", f"must be 0 on a {self.kind} lease, got {share}"
                )
            if self.kind is LeaseKind.OWNER and self.landlord.strip():
                raise ValidationError("landlord", "an owner lease has no landlord")
            object.__setattr__(
                self,
                "landlord",
                reference(self.landlord, "landlord") if self.landlord.strip() else "",
            )
        object.__setattr__(self, "landlord_share", share)

    @property
    def tenant_share(self) -> Decimal:
        """What the tenant keeps of the settlement total."""
        return Decimal(1) - self.landlord_share

    @property
    def splits(self) -> bool:
        """Whether a settlement under this lease has two parties on it."""
        return self.kind is LeaseKind.SHARE
