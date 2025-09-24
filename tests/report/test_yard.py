"""The standing shows everything, the queue shows what can actually gin."""

from __future__ import annotations

from decimal import Decimal

from ginstand.model.hold import HoldReason
from ginstand.report.yard import ginning_queue, holds, standing
from ginstand.store.book import Book
from ginstand.yard.holds import place
from ginstand.yard.receiving import receive

from .conftest import TODAY, a_module


def test_an_empty_yard_says_so(book: Book) -> None:
    lines = standing(book, TODAY).render()
    assert lines[-1] == "the yard is empty"


def test_the_standing_lists_the_worst_module_first(book: Book) -> None:
    receive(book, a_module("M-1", moisture_pct=Decimal("8.0")))
    receive(book, a_module("M-2", moisture_pct=Decimal("12.0")))
    lines = standing(book, TODAY).render()
    assert "M-2" in lines[4]
    assert "M-1" in lines[5]


def test_the_standing_carries_the_producer_and_the_points(book: Book) -> None:
    receive(book, a_module("M-1", moisture_pct=Decimal("12.0")))
    text = standing(book, TODAY).text()
    assert "P-12" in text
    assert "12.0%" in text
    assert "40.0" in text


def test_a_held_module_shows_its_reason_on_the_standing(book: Book) -> None:
    receive(book, a_module("M-1"))
    place(book, "M-1", HoldReason.PLASTIC, TODAY)
    assert "plastic" in standing(book, TODAY).text()


def test_an_at_risk_module_is_marked_when_nothing_is_holding_it(book: Book) -> None:
    receive(book, a_module("M-1", moisture_pct=Decimal("13.0")))
    assert "at risk" in standing(book, TODAY).text()


def test_the_standing_totals_the_seed_cotton(book: Book) -> None:
    receive(book, a_module("M-1"))
    receive(book, a_module("M-2"))
    assert "44,120 lb" in standing(book, TODAY).text()


def test_the_queue_leaves_out_what_is_held(book: Book) -> None:
    receive(book, a_module("M-1"))
    receive(book, a_module("M-2"))
    place(book, "M-1", HoldReason.WET, TODAY)
    text = ginning_queue(book, TODAY).text()
    assert "M-2" in text
    assert "M-1" not in text


def test_a_yard_with_everything_held_has_an_empty_queue(book: Book) -> None:
    receive(book, a_module("M-1"))
    place(book, "M-1", HoldReason.WET, TODAY)
    assert ginning_queue(book, TODAY).render()[-1] == "nothing is free to gin"


def test_the_queue_numbers_the_positions(book: Book) -> None:
    receive(book, a_module("M-1", moisture_pct=Decimal("8.0")))
    receive(book, a_module("M-2", moisture_pct=Decimal("12.0")))
    lines = ginning_queue(book, TODAY).render()
    assert lines[4].strip().startswith("1")
    assert "M-2" in lines[4]
    assert lines[5].strip().startswith("2")


def test_the_queue_can_be_run_without_grouping(book: Book) -> None:
    receive(book, a_module("M-1", field="FL-9"))
    receive(book, a_module("M-2", field="FL-5"))
    assert ginning_queue(book, TODAY, group=False).render()[2].startswith("no ")


def test_the_hold_list_is_empty_when_nothing_is_held(book: Book) -> None:
    receive(book, a_module("M-1"))
    assert holds(book, TODAY).render()[-1] == "nothing is held"


def test_the_hold_list_names_who_placed_it_and_for_how_long(book: Book) -> None:
    receive(book, a_module("M-1"))
    place(book, "M-1", HoldReason.WEIGHT, book.modules.get("M-1").received, "R Ellis")
    text = holds(book, TODAY).text()
    assert "weight" in text
    assert "R Ellis" in text
    assert "10" in text
