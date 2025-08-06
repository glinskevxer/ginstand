"""Filing is per card, so two bad records do not hold up three hundred good ones."""

from __future__ import annotations

from datetime import date

from ginstand.classing.filing import check, file_card, file_reading, outstanding
from ginstand.classing.ingest import read
from ginstand.store.book import Book


def record(sequence: int = 61, classed: str = "20251022", leaf: str = "3") -> str:
    return f"2541207{sequence:05d}{classed}31{leaf}35043294812006BK1      MEM "


def test_a_card_files_against_its_bale(book: Book) -> None:
    assert file_card(book, read(record()).cards[0]) == "filed"
    assert book.cards.get("254120700061").leaf == 3


def test_a_card_for_a_bale_nobody_pressed_is_rejected(book: Book) -> None:
    card = read(record(999)).cards[0]
    assert check(book, card, recheck=False) == "no bale in the book carries this tag"
    assert file_card(book, card) == "no bale in the book carries this tag"


def test_a_card_dated_before_the_bale_was_pressed_is_rejected(book: Book) -> None:
    card = read(record(classed="20251001")).cards[0]
    assert "the bale was pressed on 2025-10-14" in file_card(book, card)


def test_a_card_dated_the_day_the_bale_was_pressed_is_taken(book: Book) -> None:
    assert file_card(book, read(record(classed="20251014")).cards[0]) == "filed"


def test_a_second_card_is_rejected_unless_the_file_is_a_recheck(book: Book) -> None:
    file_card(book, read(record()).cards[0])
    second = read(record(leaf="4")).cards[0]
    assert file_card(book, second) == "the bale already has a card, and this file is not a recheck"
    assert book.cards.get("254120700061").leaf == 3


def test_a_recheck_replaces_the_card(book: Book) -> None:
    file_card(book, read(record()).cards[0])
    second = read(record(leaf="4", classed="20251103")).cards[0]
    assert file_card(book, second, recheck=True) == "replaced"
    assert book.cards.get("254120700061").leaf == 4
    assert book.cards.get("254120700061").classed == date(2025, 11, 3)


def test_a_whole_file_files_and_reports_what_happened(book: Book) -> None:
    reading = read(f"{record(61)}\n{record(62)}\n{record(999)}\n")
    filing = file_reading(book, reading)
    assert filing.filed == ("254120700061", "254120700062")
    assert filing.replaced == ()
    assert len(filing.rejected) == 1
    assert filing.rejected[0].tag == "254120700999"
    assert not filing.clean
    assert filing.summary == "2 filed, 0 replaced, 1 rejected"


def test_the_good_records_file_even_when_others_do_not(book: Book) -> None:
    reading = read(f"{record(999)}\n{record(61)}\n")
    file_reading(book, reading)
    assert book.cards.exists("254120700061")


def test_a_recheck_file_replaces_and_files_in_the_same_pass(book: Book) -> None:
    file_reading(book, read(record(61)))
    reading = read(f"{record(61, leaf='4')}\n{record(62)}\n")
    filing = file_reading(book, reading, recheck=True)
    assert filing.replaced == ("254120700061",)
    assert filing.filed == ("254120700062",)
    assert filing.summary == "1 filed, 1 replaced, 0 rejected"


def test_a_clean_file_reports_clean(book: Book) -> None:
    filing = file_reading(book, read(f"{record(61)}\n{record(62)}\n"))
    assert filing.clean


def test_the_bales_still_waiting_on_a_card_can_be_listed(book: Book) -> None:
    assert len(outstanding(book)) == 3
    file_reading(book, read(record(61)))
    assert outstanding(book) == ("254120700062", "254120700063")
