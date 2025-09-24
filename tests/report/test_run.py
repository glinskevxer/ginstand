"""Three tables, because the manager, the shipper and the office read different parts."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ginstand.classing.color import ColorGrade
from ginstand.ginning.allocate import allocate
from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.ginning.seed import record_load
from ginstand.model.classing import Classing
from ginstand.report.run import (
    allocation_sheet,
    bale_sheet,
    feed_sheet,
    run_sheet,
    turnout_lines,
)
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

from .conftest import a_module

OPENED = date(2025, 10, 14)


def gin(book: Book, bales: int = 10, close: bool = True, split: bool = False) -> None:
    open_run(book, "GR-1", "41207", OPENED)
    receive(book, a_module("M-1", gross_pounds=46_140, tare_pounds=26_140))
    feed(book, "GR-1", "M-1", OPENED)
    if split:
        receive(book, a_module("M-2", field="FL-5", gross_pounds=36_140, tare_pounds=26_140))
        feed(book, "GR-1", "M-2", OPENED)
    for _ in range(bales):
        press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
    if close:
        close_run(book, "GR-1", OPENED)
        allocate(book, "GR-1", OPENED)


def test_the_feed_sheet_numbers_the_modules_in_order(book: Book) -> None:
    gin(book, split=True)
    text = feed_sheet(book, "GR-1").text()
    assert "M-1" in text
    assert "M-2" in text
    assert "30,000 lb" in text


def test_the_feed_sheet_says_whether_the_run_is_open(book: Book) -> None:
    gin(book, close=False)
    assert "(open)" in feed_sheet(book, "GR-1").render()[0]
    close_run(book, "GR-1", OPENED)
    assert "closed 2025-10-14" in feed_sheet(book, "GR-1").render()[0]


def test_an_empty_run_says_nothing_has_been_fed(book: Book) -> None:
    open_run(book, "GR-1", "41207", OPENED)
    assert feed_sheet(book, "GR-1").render()[-1] == "nothing has been fed into this run"


def test_the_bale_sheet_carries_the_owner_and_the_classing(book: Book) -> None:
    gin(book, bales=2)
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
    text = bale_sheet(book, "GR-1").text()
    assert "P-12" in text
    assert "31-3 35 mic 4.3" in text
    assert "not classed" in text


def test_a_run_with_no_bales_says_so(book: Book) -> None:
    gin(book, bales=0, close=False)
    assert bale_sheet(book, "GR-1").render()[-1] == "no bales have come off this run"


def test_the_allocation_sheet_shows_the_carry_both_ways(book: Book) -> None:
    gin(book, bales=3, split=True)
    text = allocation_sheet(book, "GR-1").text()
    assert "carried in" in text
    assert "carried out" in text
    assert "P-12" in text
    assert "P-40" in text


def test_the_turnout_line_reads_final_once_the_run_is_closed(book: Book) -> None:
    gin(book)
    assert "(final)" in turnout_lines(book, "GR-1")[0]


def test_the_turnout_line_reads_so_far_while_the_run_is_open(book: Book) -> None:
    gin(book, close=False)
    assert "(so far)" in turnout_lines(book, "GR-1")[0]


def test_the_seed_turnout_appears_once_a_load_is_booked(book: Book) -> None:
    gin(book)
    assert len(turnout_lines(book, "GR-1")) == 1
    record_load(book, "GR-1", OPENED, 9_800)
    lines = turnout_lines(book, "GR-1")
    assert len(lines) == 2
    assert "9,800 lb" in lines[1]


def test_the_whole_sheet_runs_feed_then_turnout_then_bales(book: Book) -> None:
    gin(book)
    lines = run_sheet(book, "GR-1")
    assert lines[0].startswith("Gin run GR-1 feed sheet")
    assert any("turnout (final)" in line for line in lines)
    assert any(line.startswith("Gin run GR-1 bales") for line in lines)
    assert any(line.startswith("Gin run GR-1 allocation") for line in lines)


def test_a_run_with_nothing_in_it_has_no_turnout_yet(book: Book) -> None:
    open_run(book, "GR-1", "41207", OPENED)
    lines = run_sheet(book, "GR-1")
    assert "no turnout yet" in lines
    assert not any(line.startswith("Gin run GR-1 allocation") for line in lines)
