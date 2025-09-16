"""A share carries the seed cotton behind it broken down by lease."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.classing.color import ColorGrade
from ginstand.errors import StateError
from ginstand.ginning.run import close_run
from ginstand.model.classing import Classing
from ginstand.settle.gather import gather, gather_all, producers_in
from ginstand.store.book import Book

from .conftest import OPENED, gin_a_run, press_a_run


def test_a_share_carries_the_modules_and_the_bales(book: Book) -> None:
    gin_a_run(book)
    share = gather(book, "GR-1", "p-12")
    assert share.producer == "P-12"
    assert share.module_tags == ("M-1", "M-2")
    assert share.seed_cotton_pounds == 30_000
    assert share.modules == 2
    assert share.bales == 6
    assert share.lint_pounds == 6 * 490


def test_the_other_producer_gets_the_rest(book: Book) -> None:
    gin_a_run(book)
    share = gather(book, "GR-1", "P-40")
    assert share.module_tags == ("M-3",)
    assert share.seed_cotton_pounds == 10_000
    assert share.bales == 2


def test_the_seed_cotton_is_broken_down_by_lease(book: Book) -> None:
    gin_a_run(book)
    share = gather(book, "GR-1", "P-12")
    assert share.lease_pounds == {"L-1": 20_000, "L-2": 10_000}
    assert share.leases == ("L-1", "L-2")


def test_a_producer_on_one_lease_has_one_entry(book: Book) -> None:
    gin_a_run(book)
    assert gather(book, "GR-1", "P-40").lease_pounds == {"L-3": 10_000}


def test_every_bale_is_unclassed_until_a_card_arrives(book: Book) -> None:
    gin_a_run(book)
    share = gather(book, "GR-1", "P-12")
    assert share.classed == ()
    assert len(share.unclassed) == 6
    assert not share.complete


def test_a_card_moves_a_bale_into_the_classed_list(book: Book) -> None:
    gin_a_run(book)
    share = gather(book, "GR-1", "P-12")
    book.cards.add(
        Classing(
            tag=share.bale_tags[0],
            classed=date(2025, 10, 22),
            color=ColorGrade(31),
            leaf=3,
            staple=35,
            micronaire=Decimal("4.3"),
            strength=Decimal("29.4"),
            uniformity=Decimal("81.2"),
        )
    )
    again = gather(book, "GR-1", "P-12")
    assert again.classed == (share.bale_tags[0],)
    assert len(again.unclassed) == 5


def test_an_open_run_cannot_be_settled(book: Book) -> None:
    press_a_run(book)
    with pytest.raises(StateError, match="still open, so it cannot be settled"):
        gather(book, "GR-1", "P-12")


def test_an_unallocated_run_cannot_be_settled(book: Book) -> None:
    press_a_run(book)
    close_run(book, "GR-1", OPENED)
    with pytest.raises(StateError, match="has not been allocated yet"):
        gather(book, "GR-1", "P-12")


def test_a_producer_with_nothing_on_the_run_is_refused(book: Book) -> None:
    gin_a_run(book, feeds=(("M-1", "FL-9", 20_000),))
    with pytest.raises(StateError, match="has nothing on gin run GR-1"):
        gather(book, "GR-1", "P-40")


def test_the_producers_read_back_in_feed_order(book: Book) -> None:
    gin_a_run(
        book,
        feeds=(("M-3", "FL-5", 10_000), ("M-1", "FL-9", 20_000), ("M-2", "FL-2", 10_000)),
    )
    assert producers_in(book, "gr-1") == ("P-40", "P-12")
    assert [share.producer for share in gather_all(book, "GR-1")] == ["P-40", "P-12"]


def test_the_share_line_reads_as_a_settlement_list_row(book: Book) -> None:
    gin_a_run(book)
    assert gather(book, "GR-1", "P-12").line == ("P-12  2 modules  30,000 lb  6 bales, 6 unclassed")
