"""One page that either says the book is fine or says what to look at."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.report.doctor import diagnose
from ginstand.store.book import Book
from ginstand.store.migrations import latest_version
from ginstand.yard.receiving import receive

from .conftest import a_module

OPENED = date(2025, 10, 14)
TODAY = date(2025, 10, 20)


def gin(book: Book, allocate_it: bool = True) -> None:
    from ginstand.ginning.allocate import allocate

    open_run(book, "GR-1", "41207", OPENED)
    receive(book, a_module("M-1", gross_pounds=46_140, tare_pounds=26_140))
    feed(book, "GR-1", "M-1", OPENED)
    for _ in range(3):
        press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
    close_run(book, "GR-1", OPENED)
    if allocate_it:
        allocate(book, "GR-1", OPENED)


def test_an_empty_book_is_clean(book: Book) -> None:
    found = diagnose(book, TODAY)
    assert found.sound
    assert found.clean
    assert "nothing to look at" in "\n".join(found.lines)


def test_the_schema_version_is_reported(book: Book) -> None:
    found = diagnose(book, TODAY)
    assert found.schema == latest_version()
    assert found.expected == latest_version()
    assert f"schema version {latest_version()}" in "\n".join(found.lines)


def test_a_finished_run_leaves_a_query_about_the_cards(book: Book) -> None:
    gin(book)
    found = diagnose(book, TODAY)
    assert found.faults == ()
    assert any("no card yet" in line for line in found.queries)
    assert not found.clean


def test_an_unallocated_run_is_a_fault(book: Book) -> None:
    gin(book, allocate_it=False)
    found = diagnose(book, TODAY)
    assert any("no allocation" in line for line in found.faults)


def test_the_counts_head_the_findings(book: Book) -> None:
    gin(book, allocate_it=False)
    lines = diagnose(book, TODAY).lines
    assert any(line.strip().startswith("1 faults") for line in lines)


def test_a_broken_file_stops_the_rest(book: Book) -> None:
    gin(book)
    book.connection.execute("PRAGMA foreign_keys = OFF")
    book.connection.execute("DELETE FROM gin_run WHERE ref = 'GR-1'")
    found = diagnose(book, TODAY)
    assert not found.sound
    assert found.structure
    assert found.faults == ()
    assert found.queries == ()
    assert "nothing else was checked" in "\n".join(found.lines)


def test_a_book_behind_the_code_is_not_sound(book: Book) -> None:
    book.connection.execute("DELETE FROM schema_migration WHERE version = ?", (latest_version(),))
    found = diagnose(book, TODAY)
    assert not found.sound
    assert f"this code writes {latest_version()}" in "\n".join(found.lines)


def test_the_page_names_every_finding(book: Book) -> None:
    gin(book, allocate_it=False)
    text = "\n".join(diagnose(book, TODAY).lines)
    assert "fault  GR-1" in text
    assert "query  classing" in text
