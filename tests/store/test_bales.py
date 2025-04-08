"""Bales are written once, and the next bale number comes out of the book."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.model.bale import Bale
from ginstand.model.ginrun import GinRun
from ginstand.store.bales import BaleStore
from ginstand.store.runs import RunStore

PRESSED = date(2025, 10, 14)


@pytest.fixture
def press(book: sqlite3.Connection) -> sqlite3.Connection:
    runs = RunStore(book)
    runs.add(GinRun(ref="GR-1", crop_year=2025, gin_code="41207", opened=PRESSED))
    runs.add(GinRun(ref="GR-2", crop_year=2025, gin_code="41207", opened=date(2025, 10, 20)))
    return book


def a_bale(sequence: int, **changes: object) -> Bale:
    fields: dict[str, object] = {
        "tag": f"2541207{sequence:05d}",
        "run": "GR-1",
        "pressed": PRESSED,
        "gross_pounds": 512,
        "tare_pounds": 22,
        "moisture_pct": Decimal("6.8"),
    }
    fields.update(changes)
    return Bale(**fields)  # type: ignore[arg-type]


def test_a_bale_reads_back_exactly_as_it_was_pressed(press: sqlite3.Connection) -> None:
    store = BaleStore(press)
    bale = a_bale(61, stand="3")
    store.add(bale)
    assert store.get("25-41207-00061") == bale


def test_pressing_the_same_tag_twice_is_refused(press: sqlite3.Connection) -> None:
    store = BaleStore(press)
    store.add(a_bale(61))
    with pytest.raises(DuplicateError, match="bale 254120700061 is already in the book"):
        store.add(a_bale(61, gross_pounds=500))


def test_a_bale_naming_a_run_that_is_not_there_is_refused(press: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        BaleStore(press).add(a_bale(61, run="GR-9"))


def test_a_missing_bale_behaves_like_every_other_missing_record(
    press: sqlite3.Connection,
) -> None:
    store = BaleStore(press)
    assert store.find("254120700061") is None
    assert not store.exists("254120700061")
    with pytest.raises(NotFoundError, match="no bale with reference 254120700061"):
        store.get("254120700061")


def test_bales_list_in_tag_order_which_is_the_order_they_were_pressed(
    press: sqlite3.Connection,
) -> None:
    store = BaleStore(press)
    for sequence in (63, 61, 62):
        store.add(a_bale(sequence))
    assert [b.sequence for b in store.list_all()] == [61, 62, 63]


def test_bales_list_for_one_run(press: sqlite3.Connection) -> None:
    store = BaleStore(press)
    store.add(a_bale(61))
    store.add(a_bale(62, run="GR-2", pressed=date(2025, 10, 20)))
    assert [b.sequence for b in store.for_run("gr-1")] == [61]
    assert store.count_for_run("GR-1") == 1
    assert store.count_for_run("GR-2") == 1


def test_bales_list_for_one_day(press: sqlite3.Connection) -> None:
    store = BaleStore(press)
    store.add(a_bale(61))
    store.add(a_bale(62, run="GR-2", pressed=date(2025, 10, 20)))
    assert [b.sequence for b in store.pressed_on(PRESSED)] == [61]
    assert store.pressed_on(date(2025, 10, 21)) == ()


def test_the_lint_off_a_run_adds_the_bale_nets(press: sqlite3.Connection) -> None:
    store = BaleStore(press)
    assert store.lint_pounds_for_run("GR-1") == 0
    store.add(a_bale(61, gross_pounds=512, tare_pounds=22))
    store.add(a_bale(62, gross_pounds=498, tare_pounds=21))
    assert store.lint_pounds_for_run("GR-1") == 490 + 477


def test_the_next_bale_number_comes_out_of_the_book(press: sqlite3.Connection) -> None:
    store = BaleStore(press)
    assert store.last_sequence(2025, "41207") == 0
    store.add(a_bale(1))
    store.add(a_bale(2))
    assert store.last_sequence(2025, "41207") == 2


def test_the_sequence_is_read_as_a_number_not_as_text(press: sqlite3.Connection) -> None:
    store = BaleStore(press)
    store.add(a_bale(9))
    store.add(a_bale(10))
    assert store.last_sequence(2025, "41207") == 10


def test_each_crop_year_and_gin_counts_on_its_own(press: sqlite3.Connection) -> None:
    runs = RunStore(press)
    runs.add(GinRun(ref="GR-9", crop_year=2026, gin_code="41207", opened=date(2026, 9, 8)))
    store = BaleStore(press)
    store.add(a_bale(61))
    store.add(
        Bale(
            tag="264120700004",
            run="GR-9",
            pressed=date(2026, 9, 8),
            gross_pounds=505,
            tare_pounds=21,
            moisture_pct=Decimal("6.9"),
        )
    )
    assert store.last_sequence(2025, "41207") == 61
    assert store.last_sequence(2026, "41207") == 4
    assert store.last_sequence(2025, "99999") == 0
