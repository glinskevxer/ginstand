"""The register adds the run back, and says so in words when it does not."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ginstand.charges.tariff import Basis, Tariff, TariffLine
from ginstand.classing.color import ColorGrade
from ginstand.ginning.allocate import allocate
from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.ginning.seed import record_load
from ginstand.model.classing import Classing
from ginstand.report.settlement import (
    producer_page,
    reconcile,
    register,
    statements_for,
)
from ginstand.store.book import Book
from ginstand.units.money import money
from ginstand.yard.receiving import receive

from .conftest import a_module

OPENED = date(2025, 10, 14)
ISSUED = date(2025, 11, 3)
SEED_PRICE = money("210.00")

TARIFF = Tariff(
    crop_year=2025,
    lines=(
        TariffLine("GIN", "Ginning", Basis.PER_CWT, money("3.75")),
        TariffLine("BAG", "Bagging and ties", Basis.PER_BALE, money("9.50")),
    ),
)


def gin(book: Book, bales: int = 8) -> None:
    open_run(book, "GR-1", "41207", OPENED)
    receive(book, a_module("M-1", field="FL-9", gross_pounds=46_140, tare_pounds=26_140))
    feed(book, "GR-1", "M-1", OPENED)
    receive(book, a_module("M-2", field="FL-5", gross_pounds=36_140, tare_pounds=26_140))
    feed(book, "GR-1", "M-2", OPENED)
    for _ in range(bales):
        press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
    close_run(book, "GR-1", OPENED)
    allocate(book, "GR-1", OPENED)
    record_load(book, "GR-1", OPENED, 14_000)


def class_all(book: Book) -> None:
    for bale in book.bales.list_all():
        book.cards.add(
            Classing(
                tag=bale.tag,
                classed=date(2025, 10, 22),
                color=ColorGrade(31),
                leaf=3,
                staple=34,
                micronaire=Decimal("4.5"),
                strength=Decimal("27.0"),
                uniformity=Decimal("81.0"),
            )
        )


def test_the_register_lists_every_producer_in_feed_order(book: Book) -> None:
    gin(book)
    class_all(book)
    lines = register(book, "GR-1", TARIFF, SEED_PRICE, ISSUED).render()
    assert "P-12" in lines[4]
    assert "P-40" in lines[5]


def test_the_register_totals_the_columns(book: Book) -> None:
    gin(book)
    class_all(book)
    statements = statements_for(book, "GR-1", TARIFF, SEED_PRICE, ISSUED)
    text = register(book, "GR-1", TARIFF, SEED_PRICE, ISSUED).text()
    assert f"{sum(s.share.seed_cotton_pounds for s in statements):,}" in text
    assert str(sum(s.share.bales for s in statements)) in text


def test_an_unclassed_producer_is_marked_provisional(book: Book) -> None:
    gin(book)
    assert "provisional" in register(book, "GR-1", TARIFF, SEED_PRICE, ISSUED).text()


def test_a_fully_classed_run_reconciles(book: Book) -> None:
    gin(book)
    class_all(book)
    lines = reconcile(book, "GR-1", TARIFF, SEED_PRICE, ISSUED)
    assert lines == ("GR-1 reconciles: 8 bales, 30,000 lb seed cotton",)


def test_reconciling_names_the_provisional_producers(book: Book) -> None:
    gin(book)
    lines = reconcile(book, "GR-1", TARIFF, SEED_PRICE, ISSUED)
    assert any(line.startswith("provisional for") for line in lines)


def test_every_bale_and_pound_is_settled_to_somebody(book: Book) -> None:
    gin(book)
    class_all(book)
    statements = statements_for(book, "GR-1", TARIFF, SEED_PRICE, ISSUED)
    assert sum(s.share.bales for s in statements) == book.bales.count_for_run("GR-1")
    assert sum(s.share.seed_cotton_pounds for s in statements) == book.runs.seed_cotton_in("GR-1")


def test_the_producer_page_carries_the_statement_and_the_bales(book: Book) -> None:
    gin(book)
    class_all(book)
    lines = producer_page(book, "GR-1", "P-12", TARIFF, SEED_PRICE, ISSUED)
    assert lines[0].startswith("Gin run GR-1   P-12")
    assert any("254120700001" in line for line in lines)
    assert any("31-3 34 mic 4.5" in line for line in lines)


def test_the_producer_page_marks_bales_with_no_card(book: Book) -> None:
    gin(book)
    lines = producer_page(book, "GR-1", "P-12", TARIFF, SEED_PRICE, ISSUED)
    assert any("not classed" in line for line in lines)
    assert any("PROVISIONAL" in line for line in lines)
