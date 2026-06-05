"""The audit finds the state no single write was wrong about."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from ginstand.classing.recheck import CHASE_AFTER_DAYS, request
from ginstand.ginning.allocate import allocate
from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.grades.color import ColorGrade
from ginstand.model.classing import Classing
from ginstand.model.instrument import Instrument, InstrumentKind
from ginstand.model.recheck import RecheckReason
from ginstand.model.warehouse import Warehouse
from ginstand.quality.calibration import record
from ginstand.report.audit import (
    LONG_RUN_DAYS,
    Severity,
    audit,
    audit_table,
    faults,
)
from ginstand.store.book import Book
from ginstand.warehouse.receipts import issue
from ginstand.yard.receiving import receive

from .conftest import a_module

OPENED = date(2025, 10, 14)
TODAY = date(2025, 10, 20)


def gin(book: Book, close: bool = True, allocate_it: bool = True) -> None:
    open_run(book, "GR-1", "41207", OPENED)
    receive(book, a_module("M-1", gross_pounds=46_140, tare_pounds=26_140))
    feed(book, "GR-1", "M-1", OPENED)
    for _ in range(4):
        press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
    if close:
        close_run(book, "GR-1", OPENED)
        if allocate_it:
            allocate(book, "GR-1", OPENED)


def test_an_empty_book_is_consistent(book: Book) -> None:
    assert audit(book, TODAY) == ()
    assert audit_table(book, TODAY).render()[-1] == "the book is consistent"


def test_a_finished_run_is_consistent(book: Book) -> None:
    gin(book)
    assert faults(book, TODAY) == ()


def test_a_closed_run_with_no_allocation_is_a_fault(book: Book) -> None:
    gin(book, allocate_it=False)
    found = faults(book, TODAY)
    assert len(found) == 1
    assert found[0].subject == "GR-1"
    assert "no allocation" in found[0].message


def test_a_receipt_against_an_unallocated_bale_is_a_fault(book: Book) -> None:
    gin(book)
    book.warehouses.add(Warehouse(ref="WH-1", name="Delta Compress", code="41-207"))
    issue(book, "254120700001", "WH-1", date(2025, 10, 30))
    book.connection.execute("DELETE FROM bale_allocation WHERE tag = '254120700001'")
    found = faults(book, TODAY)
    assert any("has no owner" in note.message for note in found)


def test_a_receipt_held_by_somebody_who_is_not_in_the_book_is_a_fault(
    book: Book,
) -> None:
    gin(book)
    book.warehouses.add(Warehouse(ref="WH-1", name="Delta Compress", code="41-207"))
    issue(book, "254120700001", "WH-1", date(2025, 10, 30))
    book.connection.execute("PRAGMA foreign_keys = OFF")
    book.connection.execute("UPDATE receipt SET holder = 'P-99'")
    found = faults(book, TODAY)
    assert any("who is not in the book" in note.message for note in found)


def test_carries_that_do_not_cancel_are_a_fault(book: Book) -> None:
    gin(book)
    book.allocations.set_carry("P-12", 2025, Decimal("0.5"))
    found = faults(book, TODAY)
    assert any("add to 0.5" in note.message for note in found)


def test_a_carry_that_cancels_is_not_a_fault(book: Book) -> None:
    gin(book)
    book.allocations.set_carry("P-12", 2025, Decimal("0.5"))
    book.allocations.set_carry("P-40", 2025, Decimal("-0.5"))
    assert faults(book, TODAY) == ()


def test_a_run_left_open_too_long_is_a_query(book: Book) -> None:
    gin(book, close=False)
    late = date(2025, 10, 14 + LONG_RUN_DAYS + 1)
    notes = audit(book, late)
    assert any(note.severity is Severity.QUERY and note.subject == "GR-1" for note in notes)


def test_a_run_open_a_day_is_not_a_query(book: Book) -> None:
    gin(book, close=False)
    assert not any(note.subject == "GR-1" for note in audit(book, date(2025, 10, 15)))


def test_a_module_past_the_risk_line_is_a_query(book: Book) -> None:
    receive(book, a_module("M-9", moisture_pct=Decimal("13.0")))
    notes = audit(book, TODAY)
    assert any("spoil points" in note.message for note in notes)


def test_bales_with_no_card_are_one_query_rather_than_many(book: Book) -> None:
    gin(book)
    notes = [note for note in audit(book, TODAY) if note.subject == "classing"]
    assert len(notes) == 1
    assert "4 bales have no card yet" in notes[0].message


def test_faults_sort_ahead_of_queries(book: Book) -> None:
    gin(book, allocate_it=False)
    notes = audit(book, TODAY)
    severities = [note.severity for note in notes]
    assert severities == sorted(severities, key=lambda s: s is Severity.QUERY)


def test_the_table_counts_both_kinds(book: Book) -> None:
    gin(book, allocate_it=False)
    text = audit_table(book, TODAY).text()
    assert "faults" in text
    assert "queries" in text


def test_a_note_prints_as_one_line(book: Book) -> None:
    gin(book, allocate_it=False)
    assert faults(book, TODAY)[0].line.startswith("fault  GR-1")


def test_a_consistent_book_prints_no_counts(book: Book) -> None:
    lines = audit_table(book, TODAY).render()
    assert lines[-1] == "the book is consistent"
    assert not any("faults" in line for line in lines)


def a_scale(book: Book, ref: str = "SC-1") -> None:
    book.instruments.add(
        Instrument(ref=ref, kind=InstrumentKind.TRUCK_SCALE, description="Weighbridge")
    )


def test_an_instrument_never_checked_is_a_query(book: Book) -> None:
    a_scale(book)
    notes = audit(book, TODAY)
    assert any(note.subject == "SC-1" and note.severity is Severity.QUERY for note in notes)


def test_tickets_off_an_unvouched_scale_are_a_fault(book: Book) -> None:
    a_scale(book)
    gin(book)
    found = faults(book, TODAY)
    assert any("were written while it was not vouched for" in note.message for note in found)


def test_a_checked_scale_leaves_nothing_behind(book: Book) -> None:
    a_scale(book)
    gin(book)
    record(book, "SC-1", date(2025, 9, 1), Decimal("12"))
    found = faults(book, TODAY)
    assert not any("vouched" in note.message for note in found)


def test_a_recheck_out_too_long_is_a_query(book: Book) -> None:
    gin(book)
    book.cards.add(
        Classing(
            tag="254120700001",
            classed=date(2025, 10, 20),
            color=ColorGrade(31),
            leaf=3,
            staple=35,
            micronaire=Decimal("4.3"),
            strength=Decimal("29.4"),
            uniformity=Decimal("81.2"),
        )
    )
    request(book, "254120700001", RecheckReason.LEAF, date(2025, 10, 21))
    late = date(2025, 10, 21) + timedelta(days=CHASE_AFTER_DAYS + 1)
    notes = audit(book, late)
    assert any("at the classing office" in note.message for note in notes)
