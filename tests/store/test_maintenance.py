"""Backing the book up, and the two integrity questions."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ginstand.errors import StateError
from ginstand.model.bale import Bale
from ginstand.model.ginrun import GinRun
from ginstand.model.producer import Producer
from ginstand.store.book import Book
from ginstand.store.maintenance import (
    backup,
    check,
    compact,
    counts,
    dangling,
    integrity,
)


@pytest.fixture
def stocked(tmp_path: Path) -> Iterator[Book]:
    book = Book.create(tmp_path / "book.sqlite3", date(2025, 8, 4))
    book.producers.add(Producer(ref="P-12", name="Aldys Brothers"))
    book.runs.add(GinRun(ref="GR-1", crop_year=2025, gin_code="41207", opened=date(2025, 10, 14)))
    book.bales.add(
        Bale(
            tag="254120700001",
            run="GR-1",
            pressed=date(2025, 10, 14),
            gross_pounds=512,
            tare_pounds=22,
            moisture_pct=Decimal("6.8"),
        )
    )
    try:
        yield book
    finally:
        book.close()


def test_a_backup_is_a_book_that_opens(stocked: Book, tmp_path: Path) -> None:
    target = backup(stocked, tmp_path / "copy.sqlite3")
    assert target.is_file()
    with Book.open(target) as copy:
        assert copy.producers.get("P-12").name == "Aldys Brothers"
        assert copy.bales.count() == 1


def test_backing_up_over_something_is_refused(stocked: Book, tmp_path: Path) -> None:
    target = tmp_path / "copy.sqlite3"
    target.write_text("in the way")
    with pytest.raises(StateError, match="is already there"):
        backup(stocked, target)


def test_a_backup_folder_is_made_if_it_is_not_there(stocked: Book, tmp_path: Path) -> None:
    target = backup(stocked, tmp_path / "deep" / "copy.sqlite3")
    assert target.is_file()


def test_the_backup_is_a_copy_and_not_a_link(stocked: Book, tmp_path: Path) -> None:
    target = backup(stocked, tmp_path / "copy.sqlite3")
    stocked.producers.add(Producer(ref="P-40", name="Merrick Land Co"))
    with Book.open(target) as copy:
        assert copy.producers.count() == 1
    assert stocked.producers.count() == 2


def test_a_sound_book_has_nothing_wrong_with_it(stocked: Book) -> None:
    assert integrity(stocked) == ()
    assert dangling(stocked) == ()
    assert check(stocked) == ()


def test_a_record_pointing_at_nothing_is_found(stocked: Book) -> None:
    stocked.connection.execute("PRAGMA foreign_keys = OFF")
    stocked.connection.execute("DELETE FROM gin_run WHERE ref = 'GR-1'")
    found = dangling(stocked)
    assert len(found) == 1
    assert found[0].table == "bale"
    assert found[0].points_at == "gin_run"
    assert "points at gin_run" in found[0].line
    assert check(stocked)


def test_the_counts_cover_every_table(stocked: Book) -> None:
    found = counts(stocked)
    assert found["producer"] == 1
    assert found["bale"] == 1
    assert found["module"] == 0
    assert "schema_migration" in found


def test_the_counts_are_in_name_order(stocked: Book) -> None:
    assert list(counts(stocked)) == sorted(counts(stocked))


def test_compacting_leaves_the_records_alone(stocked: Book) -> None:
    compact(stocked)
    assert stocked.producers.count() == 1
    assert stocked.bales.count() == 1


def test_compacting_inside_a_transaction_is_refused(stocked: Book) -> None:
    with stocked.writing() as writing:
        with pytest.raises(StateError, match="has a transaction open"):
            compact(writing)
        writing.producers.add(Producer(ref="P-40", name="Merrick Land Co"))
