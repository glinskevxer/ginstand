"""Creating and opening a book are different operations, and that is on purpose."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ginstand.errors import DuplicateError, StateError
from ginstand.model.producer import Producer
from ginstand.store.book import Book
from ginstand.store.migrations import latest_version

DAY = date(2025, 8, 4)


def test_a_created_book_is_at_the_version_this_code_writes(tmp_path: Path) -> None:
    with Book.create(tmp_path / "book.sqlite3", DAY) as book:
        assert book.schema_version == latest_version()


def test_creating_over_a_book_that_is_there_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "book.sqlite3"
    Book.create(path, DAY).close()
    with pytest.raises(StateError, match="already there, open it"):
        Book.create(path, DAY)


def test_opening_a_path_with_no_book_at_it_is_refused(tmp_path: Path) -> None:
    with pytest.raises(StateError, match="there is no book at"):
        Book.open(tmp_path / "nothing.sqlite3")


def test_opening_does_not_create_an_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "nothing.sqlite3"
    with pytest.raises(StateError):
        Book.open(path)
    assert not path.exists()


def test_a_book_written_and_read_back_keeps_its_records(tmp_path: Path) -> None:
    path = tmp_path / "book.sqlite3"
    with Book.create(path, DAY) as book, book.writing() as writing:
        writing.producers.add(Producer(ref="P-12", name="Aldys Brothers"))
    with Book.open(path) as book:
        assert book.producers.get("P-12").name == "Aldys Brothers"


def test_a_write_block_rolls_back_as_one(tmp_path: Path) -> None:
    def add_the_same_producer_twice(book: Book) -> None:
        with book.writing() as writing:
            writing.producers.add(Producer(ref="P-12", name="Aldys Brothers"))
            writing.producers.add(Producer(ref="P-12", name="Again"))

    book = Book.create(tmp_path / "book.sqlite3", DAY)
    with pytest.raises(DuplicateError):
        add_the_same_producer_twice(book)
    assert book.producers.list_all() == ()
    book.close()


def test_an_unmigrated_book_is_refused_by_open(tmp_path: Path) -> None:
    path = tmp_path / "book.sqlite3"
    import sqlite3

    sqlite3.connect(str(path)).close()
    with pytest.raises(StateError, match="is at schema version 0"):
        Book.open(path)


def test_an_old_book_can_be_brought_forward_on_purpose(tmp_path: Path) -> None:
    path = tmp_path / "book.sqlite3"
    import sqlite3

    sqlite3.connect(str(path)).close()
    with Book.open_or_upgrade(path, DAY) as book:
        assert book.schema_version == latest_version()


def test_upgrading_a_path_with_no_book_at_it_is_still_refused(tmp_path: Path) -> None:
    with pytest.raises(StateError, match="there is no book at"):
        Book.open_or_upgrade(tmp_path / "nothing.sqlite3", DAY)


def test_an_in_memory_book_needs_no_file(tmp_path: Path) -> None:
    with Book.create(":memory:", DAY) as book:
        book.producers.add(Producer(ref="P-1", name="Aldys"))
        assert book.producers.exists("P-1")
    assert list(tmp_path.iterdir()) == []


def test_every_store_is_reachable_off_the_book() -> None:
    with Book.create(":memory:", DAY) as book:
        for name in (
            "producers",
            "leases",
            "farms",
            "fields",
            "modules",
            "runs",
            "bales",
            "cards",
        ):
            assert getattr(book, name) is not None
        assert book.connection is not None


def test_the_book_can_be_used_for_a_query_of_its_own() -> None:
    with Book.create(":memory:", DAY) as book:
        book.producers.add(Producer(ref="P-1", name="Aldys"))
        row = book.connection.execute("SELECT count(*) AS n FROM producer").fetchone()
        assert row["n"] == 1


def test_a_decimal_written_through_the_book_survives(tmp_path: Path) -> None:
    from ginstand.model.farm import Farm, Field
    from ginstand.model.producer import Lease, LeaseKind

    path = tmp_path / "book.sqlite3"
    with Book.create(path, DAY) as book, book.writing() as writing:
        writing.producers.add(Producer(ref="P-1", name="Aldys"))
        writing.leases.add(Lease(ref="L-1", tenant="P-1", kind=LeaseKind.OWNER))
        writing.farms.add(Farm(ref="F-1", producer="P-1", name="Home"))
        writing.fields.add(
            Field(ref="FL-1", farm="F-1", name="North", acres=Decimal("78.40"), lease="L-1")
        )
    with Book.open(path) as book:
        assert str(book.fields.get("FL-1").acres) == "78.40"
