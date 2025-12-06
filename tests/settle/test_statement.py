"""A statement can be issued before every card arrives, and it says so."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.charges.tariff import Basis, Tariff, TariffLine
from ginstand.ginning.seed import record_load
from ginstand.grades.color import ColorGrade
from ginstand.model.classing import Classing
from ginstand.settle.gather import gather
from ginstand.settle.statement import seed_credit_for, settle
from ginstand.store.book import Book
from ginstand.units.money import format_money, money

from .conftest import OPENED, gin_a_run

ISSUED = date(2025, 11, 3)
SEED_PRICE = money("210.00")

TARIFF = Tariff(
    crop_year=2025,
    lines=(
        TariffLine("GIN", "Ginning", Basis.PER_CWT, money("3.75")),
        TariffLine("BAG", "Bagging and ties", Basis.PER_BALE, money("9.50")),
        TariffLine("HAUL", "Module hauling", Basis.PER_MODULE, money("55.00")),
    ),
)


def class_every_bale(book: Book, producer: str, **changes: object) -> None:
    share = gather(book, "GR-1", producer)
    for tag in share.bale_tags:
        fields: dict[str, object] = {
            "tag": tag,
            "classed": date(2025, 10, 22),
            "color": ColorGrade(31),
            "leaf": 3,
            "staple": 34,
            "micronaire": Decimal("4.5"),
            "strength": Decimal("27.0"),
            "uniformity": Decimal("81.0"),
        }
        fields.update(changes)
        book.cards.add(Classing(**fields))  # type: ignore[arg-type]


def test_seed_is_credited_at_a_price_per_ton() -> None:
    assert seed_credit_for(2_000, money("210.00")) == money("210.00")
    assert seed_credit_for(1_000, money("210.00")) == money("105.00")
    assert seed_credit_for(0, money("210.00")) == 0


def test_a_statement_carries_lint_seed_and_charges(book: Book) -> None:
    gin_a_run(book)
    record_load(book, "GR-1", OPENED, 20_000)
    class_every_bale(book, "P-12")
    statement = settle(book, "GR-1", "P-12", TARIFF, SEED_PRICE, ISSUED)
    assert statement.share.bales == 6
    assert statement.lint_value == money("1528.80")
    assert statement.seed_pounds == 15_000
    assert statement.seed_credit == money("1575.00")
    assert statement.charges.total == money("1292.00")
    assert statement.total == money("1811.80")


def test_the_gross_is_lint_plus_seed(book: Book) -> None:
    gin_a_run(book)
    record_load(book, "GR-1", OPENED, 20_000)
    class_every_bale(book, "P-12")
    statement = settle(book, "GR-1", "P-12", TARIFF, SEED_PRICE, ISSUED)
    assert statement.gross == statement.lint_value + statement.seed_credit
    assert statement.total == statement.gross - statement.charges.total


def test_a_statement_with_no_cards_yet_is_provisional(book: Book) -> None:
    gin_a_run(book)
    record_load(book, "GR-1", OPENED, 20_000)
    statement = settle(book, "GR-1", "P-12", TARIFF, SEED_PRICE, ISSUED)
    assert statement.provisional
    assert statement.lint is None
    assert statement.lint_value == 0
    assert any("PROVISIONAL" in line for line in statement.lines)


def test_a_fully_classed_statement_is_not_provisional(book: Book) -> None:
    gin_a_run(book)
    record_load(book, "GR-1", OPENED, 20_000)
    class_every_bale(book, "P-12")
    statement = settle(book, "GR-1", "P-12", TARIFF, SEED_PRICE, ISSUED)
    assert not statement.provisional
    assert not any("PROVISIONAL" in line for line in statement.lines)


def test_the_seed_credit_can_carry_a_poor_lot(book: Book) -> None:
    gin_a_run(book)
    record_load(book, "GR-1", OPENED, 20_000)
    class_every_bale(book, "P-12", leaf=8)
    statement = settle(book, "GR-1", "P-12", TARIFF, SEED_PRICE, ISSUED)
    assert statement.lint_value == 0
    assert statement.total > 0
    assert statement.total == statement.seed_credit - statement.charges.total


def test_a_statement_can_come_out_negative(book: Book) -> None:
    gin_a_run(book)
    class_every_bale(book, "P-12", leaf=8)
    statement = settle(book, "GR-1", "P-12", TARIFF, SEED_PRICE, ISSUED)
    assert statement.seed_credit == 0
    assert statement.total < 0


def test_the_total_is_spread_across_the_leases_behind_the_share(book: Book) -> None:
    gin_a_run(book)
    record_load(book, "GR-1", OPENED, 20_000)
    class_every_bale(book, "P-12")
    statement = settle(book, "GR-1", "P-12", TARIFF, SEED_PRICE, ISSUED)
    assert [split.lease for split in statement.splits] == ["L-1", "L-2"]
    assert sum(split.total for split in statement.splits) == statement.total


def test_the_share_lease_gives_the_landlord_a_quarter_of_its_part(book: Book) -> None:
    gin_a_run(book)
    record_load(book, "GR-1", OPENED, 20_000)
    class_every_bale(book, "P-12")
    statement = settle(book, "GR-1", "P-12", TARIFF, SEED_PRICE, ISSUED)
    share_lease = next(split for split in statement.splits if split.lease == "L-2")
    assert share_lease.landlord == "P-40"
    assert share_lease.landlord_amount == share_lease.total // 4
    owner_lease = next(split for split in statement.splits if split.lease == "L-1")
    assert not owner_lease.splits


def test_a_producer_on_one_lease_gets_one_split(book: Book) -> None:
    gin_a_run(book)
    record_load(book, "GR-1", OPENED, 20_000)
    class_every_bale(book, "P-40")
    statement = settle(book, "GR-1", "P-40", TARIFF, SEED_PRICE, ISSUED)
    assert len(statement.splits) == 1
    assert statement.splits[0].lease == "L-3"


def test_a_negative_total_still_spreads_and_adds_back(book: Book) -> None:
    gin_a_run(book)
    class_every_bale(book, "P-12", leaf=8)
    statement = settle(book, "GR-1", "P-12", TARIFF, SEED_PRICE, ISSUED)
    assert statement.total < 0
    assert sum(split.total for split in statement.splits) == statement.total


def test_an_optional_charge_is_only_billed_when_asked_for(book: Book) -> None:
    tariff = Tariff(
        crop_year=2025,
        lines=(
            *TARIFF.lines,
            TariffLine("REST", "Moisture restoration", Basis.PER_BALE, money("2.25"), True),
        ),
    )
    gin_a_run(book)
    class_every_bale(book, "P-12")
    plain = settle(book, "GR-1", "P-12", tariff, SEED_PRICE, ISSUED)
    with_rest = settle(book, "GR-1", "P-12", tariff, SEED_PRICE, ISSUED, extras=("REST",))
    assert with_rest.charges.total - plain.charges.total == money("13.50")


def test_an_unenrolled_producer_gets_no_lint_value(book: Book) -> None:
    book.producers.update(book.producers.get("P-12").__class__(ref="P-12", name="Aldys Brothers"))
    gin_a_run(book)
    class_every_bale(book, "P-12")
    statement = settle(book, "GR-1", "P-12", TARIFF, SEED_PRICE, ISSUED)
    assert statement.lint is not None
    assert statement.lint_value == 0


def test_the_printed_statement_reads_top_to_bottom(book: Book) -> None:
    gin_a_run(book)
    record_load(book, "GR-1", OPENED, 20_000)
    class_every_bale(book, "P-12")
    lines = settle(book, "GR-1", "P-12", TARIFF, SEED_PRICE, ISSUED).lines
    assert lines[0].startswith("Gin run GR-1   P-12")
    assert "lint" in lines[2]
    assert "seed credit" in lines[3]
    assert "charges" in lines[4]
    assert "total" in lines[5]
    assert format_money(money("1811.80")) in lines[5]


def test_settling_a_producer_who_is_not_on_the_run_is_refused(book: Book) -> None:
    gin_a_run(book, feeds=(("M-1", "FL-9", 20_000),))
    with pytest.raises(Exception, match="has nothing on gin run"):
        settle(book, "GR-1", "P-40", TARIFF, SEED_PRICE, ISSUED)
