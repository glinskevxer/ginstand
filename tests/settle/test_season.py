"""A producer's season, with what they grew beside what they have been paid."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.charges.published import seed_price_for, tariff_for
from ginstand.errors import StateError
from ginstand.ginning.press import press
from ginstand.ginning.run import feed, open_run
from ginstand.grades.color import ColorGrade
from ginstand.model.classing import Classing
from ginstand.settle.account import pay, post_settlement
from ginstand.settle.gather import gather
from ginstand.settle.season import for_producer
from ginstand.store.book import Book
from ginstand.units.money import money

from .conftest import a_module, gin_a_run

ISSUED = date(2025, 11, 3)
TARIFF = tariff_for(2025)
SEED = seed_price_for(2025)


def class_all(book: Book, producer: str) -> None:
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


def test_a_producer_with_no_settled_run_has_no_season(book: Book) -> None:
    gin_a_run(book)
    with pytest.raises(StateError, match="no settled run in crop year 2026"):
        for_producer(book, "P-12", 2026)


def test_the_season_totals_the_runs(book: Book) -> None:
    gin_a_run(book)
    season = for_producer(book, "P-12", 2025)
    assert season.runs == 1
    assert season.modules == 2
    assert season.seed_cotton_pounds == 30_000
    assert season.bales == 6
    assert season.lint_pounds == 6 * 490


def test_the_turnout_is_across_the_whole_season(book: Book) -> None:
    gin_a_run(book)
    assert for_producer(book, "P-12", 2025).turnout == Decimal("0.0980")


def test_the_account_sits_beside_the_totals(book: Book) -> None:
    gin_a_run(book)
    class_all(book, "P-12")
    post_settlement(book, "GR-1", "P-12", TARIFF, SEED, ISSUED)
    season = for_producer(book, "P-12", 2025)
    assert season.settled > 0
    assert season.paid == 0
    assert season.balance == season.settled


def test_a_payment_moves_the_balance_and_not_the_crop(book: Book) -> None:
    gin_a_run(book)
    class_all(book, "P-12")
    post_settlement(book, "GR-1", "P-12", TARIFF, SEED, ISSUED)
    before = for_producer(book, "P-12", 2025)
    pay(book, "P-12", 2025, money("100.00"), ISSUED)
    after = for_producer(book, "P-12", 2025)
    assert after.bales == before.bales
    assert after.paid == money("-100.00")
    assert after.balance == before.balance - money("100.00")


def test_the_unclassed_bales_are_counted_and_their_runs_named(book: Book) -> None:
    gin_a_run(book)
    season = for_producer(book, "P-12", 2025)
    assert season.unclassed == 6
    assert season.unsettled_runs == ("GR-1",)
    assert any("still waiting on a card" in line for line in season.lines)


def test_a_fully_classed_season_says_nothing_about_waiting(book: Book) -> None:
    gin_a_run(book)
    class_all(book, "P-12")
    season = for_producer(book, "P-12", 2025)
    assert season.unclassed == 0
    assert not any("waiting" in line for line in season.lines)


def test_an_open_run_is_left_out(book: Book) -> None:
    gin_a_run(book)
    open_run(book, "GR-2", "41207", date(2025, 10, 20))
    book.modules.add(a_module("M-9", "FL-9", 10_000))
    feed(book, "GR-2", "M-9", date(2025, 10, 20))
    press(book, "GR-2", date(2025, 10, 20), 512, 22, Decimal("6.8"))
    assert for_producer(book, "P-12", 2025).runs == 1
