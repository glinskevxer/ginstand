"""Working a settlement out and agreeing it are separate calls."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.charges.published import seed_price_for, tariff_for
from ginstand.errors import StateError
from ginstand.ginning.seed import record_load
from ginstand.grades.color import ColorGrade
from ginstand.model.account import EntryKind
from ginstand.model.classing import Classing
from ginstand.settle.account import adjust, balance, owing, pay, post_settlement
from ginstand.settle.gather import gather
from ginstand.store.book import Book
from ginstand.units.money import Money, money

from .conftest import OPENED, gin_a_run

ISSUED = date(2025, 11, 3)
TARIFF = tariff_for(2025)
SEED = seed_price_for(2025)


def class_every_bale(book: Book, producer: str) -> None:
    for tag in gather(book, "GR-1", producer).bale_tags:
        book.cards.add(
            Classing(
                tag=tag,
                classed=date(2025, 10, 22),
                color=ColorGrade(31),
                leaf=3,
                staple=34,
                micronaire=Decimal("4.5"),
                strength=Decimal("27.0"),
                uniformity=Decimal("81.0"),
            )
        )


def ready(book: Book) -> None:
    gin_a_run(book)
    record_load(book, "GR-1", OPENED, 20_000)
    class_every_bale(book, "P-12")
    class_every_bale(book, "P-40")


def test_posting_a_settlement_puts_it_on_the_account(book: Book) -> None:
    ready(book)
    statement, entry = post_settlement(book, "GR-1", "P-12", TARIFF, SEED, ISSUED)
    assert entry.kind is EntryKind.SETTLEMENT
    assert entry.amount == statement.total
    assert balance(book, "P-12", 2025) == statement.total


def test_a_provisional_statement_cannot_be_posted(book: Book) -> None:
    gin_a_run(book)
    with pytest.raises(StateError, match="is provisional, with 6 bales unclassed"):
        post_settlement(book, "GR-1", "P-12", TARIFF, SEED, ISSUED)


def test_posting_the_same_run_twice_names_the_entry_in_the_way(book: Book) -> None:
    ready(book)
    post_settlement(book, "GR-1", "P-12", TARIFF, SEED, ISSUED)
    with pytest.raises(StateError, match="was already settled for GR-1 on 2025-11-03"):
        post_settlement(book, "GR-1", "P-12", TARIFF, SEED, date(2025, 11, 4))


def test_an_adjustment_moves_the_balance(book: Book) -> None:
    ready(book)
    post_settlement(book, "GR-1", "P-12", TARIFF, SEED, ISSUED)
    before = balance(book, "P-12", 2025)
    adjust(book, "P-12", 2025, money("-40.00"), ISSUED, "module weight corrected")
    assert balance(book, "P-12", 2025) == before - money("40.00")


def test_an_adjustment_needs_a_reason(book: Book) -> None:
    ready(book)
    with pytest.raises(StateError, match="needs a reason on it"):
        adjust(book, "P-12", 2025, money("40.00"), ISSUED, "  ")


def test_an_adjustment_against_a_run_that_is_not_there_is_refused(book: Book) -> None:
    ready(book)
    with pytest.raises(Exception, match="no gin run with reference GR-9"):
        adjust(book, "P-12", 2025, money("40.00"), ISSUED, "why", run="GR-9")


def test_a_payment_is_typed_positive_and_stored_negative(book: Book) -> None:
    ready(book)
    post_settlement(book, "GR-1", "P-12", TARIFF, SEED, ISSUED)
    entry = pay(book, "P-12", 2025, money("100.00"), ISSUED, "CHQ-4471")
    assert entry.amount == money("-100.00")
    assert entry.reference == "CHQ-4471"


def test_a_payment_bigger_than_the_balance_is_refused(book: Book) -> None:
    ready(book)
    post_settlement(book, "GR-1", "P-12", TARIFF, SEED, ISSUED)
    owed = balance(book, "P-12", 2025)
    with pytest.raises(StateError, match="is owed"):
        pay(book, "P-12", 2025, Money(owed + money("0.01")), ISSUED)


def test_a_payment_of_the_whole_balance_squares_the_account(book: Book) -> None:
    ready(book)
    post_settlement(book, "GR-1", "P-12", TARIFF, SEED, ISSUED)
    pay(book, "P-12", 2025, balance(book, "P-12", 2025), ISSUED)
    assert balance(book, "P-12", 2025) == 0


def test_a_payment_of_nothing_is_not_a_payment(book: Book) -> None:
    ready(book)
    post_settlement(book, "GR-1", "P-12", TARIFF, SEED, ISSUED)
    with pytest.raises(StateError, match="is not a payment"):
        pay(book, "P-12", 2025, money("0"), ISSUED)


def test_the_owing_list_leaves_out_the_squared_accounts(book: Book) -> None:
    ready(book)
    post_settlement(book, "GR-1", "P-12", TARIFF, SEED, ISSUED)
    post_settlement(book, "GR-1", "P-40", TARIFF, SEED, ISSUED)
    pay(book, "P-40", 2025, balance(book, "P-40", 2025), ISSUED)
    found = owing(book, 2025)
    assert list(found) == ["P-12"]


def test_the_owing_list_is_most_owed_first(book: Book) -> None:
    ready(book)
    post_settlement(book, "GR-1", "P-12", TARIFF, SEED, ISSUED)
    post_settlement(book, "GR-1", "P-40", TARIFF, SEED, ISSUED)
    amounts = list(owing(book, 2025).values())
    assert amounts == sorted(amounts, reverse=True)


def test_a_producer_who_is_not_in_the_book_is_refused(book: Book) -> None:
    ready(book)
    with pytest.raises(Exception, match="no producer with reference P-99"):
        adjust(book, "P-99", 2025, money("40.00"), ISSUED, "why")
