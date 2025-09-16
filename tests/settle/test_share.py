"""The split runs on the total and the two parts add back to it exactly."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ginstand.errors import ValidationError
from ginstand.model.producer import Lease, LeaseKind
from ginstand.settle.share import LeaseSplit, split_settlement
from ginstand.units.money import Money, format_money, money

OWNER = Lease(ref="L-1", tenant="P-12", kind=LeaseKind.OWNER)
QUARTER = Lease(
    ref="L-2",
    tenant="P-12",
    kind=LeaseKind.SHARE,
    landlord="P-40",
    landlord_share=Decimal("0.25"),
)
THIRD = Lease(
    ref="L-3",
    tenant="P-12",
    kind=LeaseKind.SHARE,
    landlord="P-40",
    landlord_share=Decimal("0.3333"),
)
CASH = Lease(ref="L-4", tenant="P-12", kind=LeaseKind.CASH, landlord="P-40")


def test_an_owner_lease_gives_the_whole_settlement_to_the_tenant() -> None:
    split = split_settlement(money("1000.00"), OWNER)
    assert split.tenant_amount == money("1000.00")
    assert split.landlord_amount == 0
    assert split.landlord == ""
    assert not split.splits


def test_a_cash_lease_gives_the_landlord_none_of_the_crop() -> None:
    split = split_settlement(money("1000.00"), CASH)
    assert split.tenant_amount == money("1000.00")
    assert not split.splits


def test_a_share_lease_splits_the_total() -> None:
    split = split_settlement(money("1000.00"), QUARTER)
    assert split.landlord_amount == money("250.00")
    assert split.tenant_amount == money("750.00")
    assert split.splits


@pytest.mark.parametrize(
    "amount",
    ["1000.00", "1000.01", "1000.02", "1000.03", "0.01", "0.03", "9999.99", "7.77"],
)
def test_the_parts_always_add_back_to_the_whole(amount: str) -> None:
    for lease in (QUARTER, THIRD):
        split = split_settlement(money(amount), lease)
        assert split.tenant_amount + split.landlord_amount == money(amount)


def test_an_awkward_third_leaves_the_odd_cent_with_the_tenant() -> None:
    split = split_settlement(money("100.01"), THIRD)
    assert split.landlord_amount == money("33.33")
    assert split.tenant_amount == money("66.68")
    assert split.tenant_amount + split.landlord_amount == money("100.01")


def test_a_settlement_the_producer_owes_splits_the_same_way() -> None:
    split = split_settlement(money("-400.00"), QUARTER)
    assert split.landlord_amount == money("-100.00")
    assert split.tenant_amount == money("-300.00")
    assert split.tenant_amount + split.landlord_amount == money("-400.00")


def test_an_awkward_negative_still_adds_back() -> None:
    split = split_settlement(money("-100.01"), THIRD)
    assert split.tenant_amount + split.landlord_amount == money("-100.01")


def test_a_charge_moves_the_landlords_share_because_the_split_is_on_the_total() -> None:
    lint_only = split_settlement(money("1000.00"), QUARTER)
    after_charges = split_settlement(Money(money("1000.00") - money("240.00")), QUARTER)
    assert lint_only.landlord_amount == money("250.00")
    assert after_charges.landlord_amount == money("190.00")


def test_a_split_that_does_not_add_back_cannot_be_built() -> None:
    with pytest.raises(ValidationError, match="do not add back"):
        LeaseSplit(
            lease="L-2",
            total=money("100.00"),
            tenant="P-12",
            tenant_amount=money("80.00"),
            landlord="P-40",
            landlord_amount=money("25.00"),
            landlord_share=Decimal("0.25"),
        )


def test_a_zero_settlement_splits_to_nothing_on_both_sides() -> None:
    split = split_settlement(Money(0), QUARTER)
    assert split.tenant_amount == 0
    assert split.landlord_amount == 0


def test_the_lines_name_the_share_on_the_landlord_row() -> None:
    split = split_settlement(money("1000.00"), QUARTER)
    assert len(split.lines) == 2
    assert split.lines[0].startswith("P-12")
    assert split.lines[1].endswith("(0.25 share)")
    assert format_money(split.landlord_amount) in split.lines[1]


def test_an_owner_lease_prints_one_line() -> None:
    assert len(split_settlement(money("1000.00"), OWNER).lines) == 1
