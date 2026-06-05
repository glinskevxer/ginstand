"""The day sheet counts what was done, including when it was nothing."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ginstand.ginning.press import press
from ginstand.ginning.run import feed, open_run
from ginstand.ginning.seed import record_load
from ginstand.grades.color import ColorGrade
from ginstand.model.classing import Classing
from ginstand.model.hold import HoldReason
from ginstand.report.daily import bale_table, full, module_table, sheet
from ginstand.store.book import Book
from ginstand.yard.holds import place
from ginstand.yard.receiving import receive

from .conftest import a_module

RECEIVED = date(2025, 10, 2)
GINNED = date(2025, 10, 14)


def a_day(book: Book) -> None:
    receive(book, a_module("M-1", received=RECEIVED))
    receive(book, a_module("M-2", received=RECEIVED))
    open_run(book, "GR-1", "41207", GINNED)
    feed(book, "GR-1", "M-1", GINNED)
    for _ in range(3):
        press(book, "GR-1", GINNED, 512, 22, Decimal("6.8"))
    record_load(book, "GR-1", GINNED, 9_800)


def test_a_day_nothing_happened_on_says_so(book: Book) -> None:
    day = sheet(book, date(2025, 10, 1))
    assert day.quiet
    assert "nothing was written down for this day" in "\n".join(day.lines)


def test_the_sheet_counts_what_came_in(book: Book) -> None:
    a_day(book)
    day = sheet(book, RECEIVED)
    assert day.modules_in == ("M-1", "M-2")
    assert day.seed_cotton_in == 2 * 22_060
    assert not day.quiet


def test_the_sheet_counts_what_was_ginned_and_pressed(book: Book) -> None:
    a_day(book)
    day = sheet(book, GINNED)
    assert day.modules_ginned == ("M-1",)
    assert day.seed_cotton_ginned == 22_060
    assert len(day.bales) == 3
    assert day.lint == 3 * 490
    assert day.seed_out == 9_800


def test_receiving_and_ginning_are_counted_on_their_own_days(book: Book) -> None:
    a_day(book)
    assert sheet(book, RECEIVED).modules_ginned == ()
    assert sheet(book, GINNED).modules_in == ()


def test_a_card_is_counted_on_the_day_it_was_classed(book: Book) -> None:
    a_day(book)
    book.cards.add(
        Classing(
            tag="254120700001",
            classed=date(2025, 10, 22),
            color=ColorGrade(31),
            leaf=3,
            staple=35,
            micronaire=Decimal("4.3"),
            strength=Decimal("29.4"),
            uniformity=Decimal("81.2"),
        )
    )
    assert sheet(book, date(2025, 10, 22)).cards == ("254120700001",)
    assert sheet(book, GINNED).cards == ()


def test_a_hold_is_counted_on_the_day_it_was_placed(book: Book) -> None:
    receive(book, a_module("M-1", received=RECEIVED))
    place(book, "M-1", HoldReason.WET, date(2025, 10, 3))
    assert sheet(book, date(2025, 10, 3)).holds_placed == ("M-1",)
    assert sheet(book, date(2025, 10, 4)).holds_placed == ()


def test_the_sheet_reads_as_a_page(book: Book) -> None:
    a_day(book)
    lines = sheet(book, GINNED).lines
    assert lines[0] == "Day sheet for 2025-10-14"
    assert any("pressed" in line for line in lines)
    assert any("seed out" in line for line in lines)


def test_the_module_list_totals_the_day(book: Book) -> None:
    a_day(book)
    text = module_table(book, RECEIVED).text()
    assert "M-1" in text
    assert "44,120 lb" in text


def test_an_empty_module_list_says_so(book: Book) -> None:
    assert module_table(book, RECEIVED).render()[-1] == "nothing crossed the scale"


def test_the_bale_list_totals_the_day(book: Book) -> None:
    a_day(book)
    text = bale_table(book, GINNED).text()
    assert "254120700001" in text
    assert "1,470 lb" in text


def test_an_empty_bale_list_says_so(book: Book) -> None:
    assert bale_table(book, GINNED).render()[-1] == "no bale came off the press"


def test_the_full_sheet_carries_both_lists(book: Book) -> None:
    a_day(book)
    lines = full(book, GINNED)
    assert lines[0].startswith("Day sheet")
    assert any(line.startswith("Weighed in on") for line in lines)
    assert any(line.startswith("Pressed on") for line in lines)
