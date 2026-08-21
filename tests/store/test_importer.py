"""Reading a book back in, in the order the schema created the tables."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ginstand.errors import StateError
from ginstand.model.farm import Farm, Field
from ginstand.model.ginrun import GinRun
from ginstand.model.producer import Lease, LeaseKind, Producer
from ginstand.store.book import Book
from ginstand.store.export import write_all
from ginstand.store.importer import (
    columns_of,
    creation_order,
    nullable,
    read_all,
    read_table,
)

DAY = date(2025, 8, 4)


@pytest.fixture
def stocked() -> Iterator[Book]:
    book = Book.create(":memory:", DAY)
    book.producers.add(Producer(ref="P-12", name="Aldys Brothers"))
    book.leases.add(Lease(ref="L-1", tenant="P-12", kind=LeaseKind.OWNER))
    book.farms.add(Farm(ref="F-3", producer="P-12", name="Home Place"))
    book.fields.add(
        Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("78.40"), lease="L-1")
    )
    book.runs.add(GinRun(ref="GR-1", crop_year=2025, gin_code="41207", opened=date(2025, 10, 14)))
    try:
        yield book
    finally:
        book.close()


def test_the_order_puts_a_run_before_the_bales_that_point_at_it() -> None:
    order = creation_order()
    assert order.index("gin_run") < order.index("bale")
    assert order.index("producer") < order.index("farm") < order.index("field")


def test_the_migration_tables_are_left_out_of_the_order() -> None:
    assert "schema_migration" not in creation_order()


def test_the_columns_come_back_in_the_order_sqlite_holds_them(
    stocked: Book,
) -> None:
    assert columns_of(stocked, "producer") == (
        "ref",
        "name",
        "address",
        "phone",
        "ccc_number",
    )


def test_a_book_round_trips_through_the_files(stocked: Book, tmp_path: Path) -> None:
    write_all(stocked, tmp_path / "out")
    with Book.create(":memory:", DAY) as fresh:
        loaded = read_all(fresh, tmp_path / "out")
        assert fresh.producers.get("P-12").name == "Aldys Brothers"
        assert fresh.fields.get("FL-9").acres == Decimal("78.40")
        assert fresh.runs.get("GR-1").crop_year == 2025
        assert sum(item.rows for item in loaded) == 5


def test_a_decimal_keeps_its_places_through_the_round_trip(stocked: Book, tmp_path: Path) -> None:
    write_all(stocked, tmp_path / "out")
    with Book.create(":memory:", DAY) as fresh:
        read_all(fresh, tmp_path / "out")
        assert str(fresh.fields.get("FL-9").acres) == "78.40"


def test_a_null_comes_back_as_a_null_and_an_empty_string_as_one(
    stocked: Book, tmp_path: Path
) -> None:
    write_all(stocked, tmp_path / "out")
    with Book.create(":memory:", DAY) as fresh:
        read_all(fresh, tmp_path / "out")
        assert fresh.runs.get("GR-1").closed is None
        assert fresh.producers.get("P-12").address == ""


def test_the_column_decides_what_an_empty_cell_means(stocked: Book) -> None:
    """The closed date allows a null and the shift does not.

    A text primary key reads as nullable, which is sqlite's own answer: only an
    integer primary key is implicitly NOT NULL and even that reports zero here.
    It does not matter, because a reference is never an empty cell.
    """
    assert nullable(stocked, "gin_run") == (True, False, False, False, True, False, False)
    assert nullable(stocked, "producer") == (True, False, False, False, False)


def test_reading_into_a_table_with_rows_in_it_is_refused(stocked: Book, tmp_path: Path) -> None:
    write_all(stocked, tmp_path / "out")
    with pytest.raises(StateError, match="already has 1 rows"):
        read_table(stocked, "producer", tmp_path / "out" / "producer.csv")


def test_a_table_the_book_has_not_got_is_refused(stocked: Book, tmp_path: Path) -> None:
    path = tmp_path / "nothing.csv"
    path.write_text("a\n")
    with pytest.raises(StateError, match="no table called nowhere"):
        read_table(stocked, "nowhere", path)


def test_a_file_with_the_wrong_columns_is_refused(stocked: Book, tmp_path: Path) -> None:
    path = tmp_path / "producer.csv"
    path.write_text("ref,name\nP-1,Aldys\n")
    with Book.create(":memory:", DAY) as fresh, pytest.raises(StateError, match="has columns"):
        read_table(fresh, "producer", path)


def test_a_file_with_no_header_is_refused(stocked: Book, tmp_path: Path) -> None:
    path = tmp_path / "producer.csv"
    path.write_text("")
    with Book.create(":memory:", DAY) as fresh, pytest.raises(StateError, match="no header row"):
        read_table(fresh, "producer", path)


def test_a_short_row_is_refused_with_its_line(stocked: Book, tmp_path: Path) -> None:
    path = tmp_path / "producer.csv"
    path.write_text("ref,name,address,phone,ccc_number\nP-1,Aldys\n")
    with (
        Book.create(":memory:", DAY) as fresh,
        pytest.raises(StateError, match="row 2 has 2 cells"),
    ):
        read_table(fresh, "producer", path)


def test_a_folder_that_is_not_there_is_refused(tmp_path: Path) -> None:
    with Book.create(":memory:", DAY) as fresh, pytest.raises(StateError, match="no folder at"):
        read_all(fresh, tmp_path / "nowhere")


def test_a_folder_with_no_table_files_is_refused(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with Book.create(":memory:", DAY) as fresh, pytest.raises(StateError, match="no table files"):
        read_all(fresh, empty)
