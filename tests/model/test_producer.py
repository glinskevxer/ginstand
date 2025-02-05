"""A producer and a lease check themselves, so an invalid one cannot be built."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ginstand.errors import ValidationError
from ginstand.model.producer import Lease, LeaseKind, Producer


def test_a_producer_normalises_its_reference_and_keeps_its_name() -> None:
    producer = Producer(ref=" p-12 ", name="  Aldys Brothers  ")
    assert producer.ref == "P-12"
    assert producer.name == "Aldys Brothers"


def test_a_producer_without_a_name_is_refused() -> None:
    with pytest.raises(ValidationError, match="producer name: is empty"):
        Producer(ref="P-12", name="   ")


def test_a_producer_without_a_reference_is_refused() -> None:
    with pytest.raises(ValidationError, match="^producer:"):
        Producer(ref="", name="Aldys Brothers")


def test_the_loan_number_is_upper_cased_and_decides_loan_eligibility() -> None:
    assert not Producer(ref="P-12", name="Aldys").enrolled_for_loan
    enrolled = Producer(ref="P-12", name="Aldys", ccc_number=" a4471 ")
    assert enrolled.ccc_number == "A4471"
    assert enrolled.enrolled_for_loan


def test_a_producer_is_frozen() -> None:
    producer = Producer(ref="P-12", name="Aldys")
    with pytest.raises(AttributeError):
        producer.name = "Someone else"  # type: ignore[misc]


def test_an_owner_lease_has_no_landlord_and_no_split() -> None:
    lease = Lease(ref="L-1", tenant="P-12", kind=LeaseKind.OWNER)
    assert lease.landlord == ""
    assert lease.landlord_share == Decimal("0")
    assert lease.tenant_share == Decimal("1")
    assert not lease.splits


def test_a_share_lease_carries_the_landlord_and_the_fraction() -> None:
    lease = Lease(
        ref="l-2",
        tenant="p-12",
        kind=LeaseKind.SHARE,
        landlord="p-40",
        landlord_share=Decimal("0.25"),
    )
    assert lease.ref == "L-2"
    assert lease.landlord == "P-40"
    assert lease.tenant_share == Decimal("0.75")
    assert lease.splits


def test_a_share_lease_without_a_landlord_is_refused() -> None:
    with pytest.raises(ValidationError, match="a share lease needs a landlord"):
        Lease(ref="L-2", tenant="P-12", kind=LeaseKind.SHARE, landlord_share=Decimal("0.25"))


@pytest.mark.parametrize("share", [Decimal("0"), Decimal("1"), Decimal("-0.1"), Decimal("1.5")])
def test_a_share_lease_needs_a_fraction_strictly_inside_zero_and_one(share: Decimal) -> None:
    with pytest.raises(ValidationError, match="above 0 and below 1"):
        Lease(ref="L-2", tenant="P-12", kind=LeaseKind.SHARE, landlord="P-40", landlord_share=share)


def test_a_cash_lease_may_name_a_landlord_but_takes_none_of_the_crop() -> None:
    lease = Lease(ref="L-3", tenant="P-12", kind=LeaseKind.CASH, landlord="P-40")
    assert lease.landlord == "P-40"
    assert lease.landlord_share == Decimal("0")
    assert not lease.splits


def test_a_cash_lease_with_a_share_on_it_is_a_contradiction() -> None:
    with pytest.raises(ValidationError, match="must be 0 on a cash lease"):
        Lease(
            ref="L-3",
            tenant="P-12",
            kind=LeaseKind.CASH,
            landlord="P-40",
            landlord_share=Decimal("0.25"),
        )


def test_an_owner_lease_with_a_landlord_is_a_contradiction() -> None:
    with pytest.raises(ValidationError, match="an owner lease has no landlord"):
        Lease(ref="L-1", tenant="P-12", kind=LeaseKind.OWNER, landlord="P-40")


def test_the_two_shares_add_to_the_whole() -> None:
    lease = Lease(
        ref="L-2",
        tenant="P-12",
        kind=LeaseKind.SHARE,
        landlord="P-40",
        landlord_share=Decimal("0.3333"),
    )
    assert lease.landlord_share + lease.tenant_share == Decimal("1")


def test_the_lease_kinds_read_as_the_words_the_office_uses() -> None:
    assert str(LeaseKind.SHARE) == "share"
    assert LeaseKind("cash") is LeaseKind.CASH
