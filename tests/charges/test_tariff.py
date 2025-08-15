"""A rate is charged against a basis, and the basis is part of the tariff."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ginstand.charges.tariff import Basis, Tariff, TariffLine, bill, units_for
from ginstand.errors import ValidationError
from ginstand.units.money import format_money, money

TARIFF = Tariff(
    crop_year=2025,
    lines=(
        TariffLine("GIN", "Ginning", Basis.PER_CWT, money("3.75")),
        TariffLine("BAG", "Bagging and ties", Basis.PER_BALE, money("9.50")),
        TariffLine("HAUL", "Module hauling", Basis.PER_MODULE, money("55.00")),
        TariffLine("CLASS", "Classing fee", Basis.PER_BALE, money("1.05")),
        TariffLine("REST", "Moisture restoration", Basis.PER_BALE, money("2.25"), optional=True),
        TariffLine("ADMIN", "Season administration", Basis.FLAT, money("40.00")),
    ),
)


def test_a_tariff_lists_its_codes_in_the_order_published() -> None:
    assert TARIFF.codes == ("GIN", "BAG", "HAUL", "CLASS", "REST", "ADMIN")


def test_a_line_can_be_looked_up_by_code() -> None:
    assert TARIFF.line("gin").rate == money("3.75")
    assert TARIFF.line(" bag ").basis is Basis.PER_BALE


def test_a_code_that_is_not_on_the_tariff_is_refused() -> None:
    with pytest.raises(ValidationError, match="NOPE is not on the 2025 tariff"):
        TARIFF.line("nope")


def test_a_tariff_with_two_lines_on_one_code_is_refused() -> None:
    with pytest.raises(ValidationError, match="has two lines coded GIN"):
        Tariff(
            crop_year=2025,
            lines=(
                TariffLine("GIN", "Ginning", Basis.PER_CWT, money("3.75")),
                TariffLine("gin", "Ginning again", Basis.PER_BALE, money("1.00")),
            ),
        )


def test_a_line_needs_a_code_and_a_description() -> None:
    with pytest.raises(ValidationError, match="charge code: is empty"):
        TariffLine("  ", "Ginning", Basis.PER_CWT, money("3.75"))
    with pytest.raises(ValidationError, match="charge description: is empty"):
        TariffLine("GIN", " ", Basis.PER_CWT, money("3.75"))


def test_a_negative_rate_is_refused() -> None:
    with pytest.raises(ValidationError, match="must not be negative"):
        TariffLine("GIN", "Ginning", Basis.PER_CWT, money("-1.00"))


@pytest.mark.parametrize(
    ("basis", "expected"),
    [
        (Basis.PER_BALE, Decimal("20")),
        (Basis.PER_MODULE, Decimal("3")),
        (Basis.PER_CWT, Decimal("600.00")),
        (Basis.FLAT, Decimal("1")),
    ],
)
def test_each_basis_counts_its_own_units(basis: Basis, expected: Decimal) -> None:
    assert units_for(basis, bales=20, seed_cotton_pounds=60_000, modules=3) == expected


def test_a_bill_charges_every_line_that_is_not_optional() -> None:
    sheet = bill(TARIFF, bales=20, seed_cotton_pounds=60_000, modules=3)
    assert [charge.code for charge in sheet.charges] == ["GIN", "BAG", "HAUL", "CLASS", "ADMIN"]


def test_an_optional_line_is_charged_only_when_it_was_asked_for() -> None:
    without = bill(TARIFF, bales=20, seed_cotton_pounds=60_000, modules=3)
    assert without.amount_for("REST") == 0
    with_it = bill(TARIFF, bales=20, seed_cotton_pounds=60_000, modules=3, extras=["rest"])
    assert with_it.amount_for("REST") == money("45.00")


def test_asking_for_a_line_that_is_not_on_the_tariff_is_refused() -> None:
    with pytest.raises(ValidationError, match="not on the 2025 tariff"):
        bill(TARIFF, bales=20, seed_cotton_pounds=60_000, modules=3, extras=["nope"])


def test_the_amounts_are_the_rate_times_the_units() -> None:
    sheet = bill(TARIFF, bales=20, seed_cotton_pounds=60_000, modules=3)
    assert sheet.amount_for("GIN") == money("2250.00")
    assert sheet.amount_for("BAG") == money("190.00")
    assert sheet.amount_for("HAUL") == money("165.00")
    assert sheet.amount_for("CLASS") == money("21.00")
    assert sheet.amount_for("ADMIN") == money("40.00")


def test_the_total_is_the_lines_added_up() -> None:
    sheet = bill(TARIFF, bales=20, seed_cotton_pounds=60_000, modules=3)
    assert sheet.total == sum(charge.amount for charge in sheet.charges)
    assert format_money(sheet.total) == "$2,666.00"


def test_ginning_on_hundredweight_does_not_move_with_the_turnout() -> None:
    good = bill(TARIFF, bales=22, seed_cotton_pounds=60_000, modules=3)
    poor = bill(TARIFF, bales=17, seed_cotton_pounds=60_000, modules=3)
    assert good.amount_for("GIN") == poor.amount_for("GIN")
    assert good.amount_for("BAG") > poor.amount_for("BAG")


def test_a_share_with_nothing_in_it_still_carries_the_flat_line() -> None:
    sheet = bill(TARIFF, bales=0, seed_cotton_pounds=0, modules=0)
    assert sheet.amount_for("GIN") == 0
    assert sheet.amount_for("ADMIN") == money("40.00")
    assert sheet.total == money("40.00")


def test_a_negative_quantity_is_refused() -> None:
    with pytest.raises(ValidationError, match="must not be negative"):
        bill(TARIFF, bales=-1, seed_cotton_pounds=0, modules=0)


def test_a_bill_prints_a_line_per_charge() -> None:
    sheet = bill(TARIFF, bales=20, seed_cotton_pounds=60_000, modules=3)
    assert len(sheet.lines) == 5
    assert sheet.lines[0].startswith("GIN    Ginning")
    assert sheet.lines[0].endswith("$2,250.00")


def test_a_line_not_charged_reads_as_zero_rather_than_raising() -> None:
    sheet = bill(TARIFF, bales=20, seed_cotton_pounds=60_000, modules=3)
    assert sheet.amount_for("REST") == 0
