"""Writing the book out as CSV, and counting what was written."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ginstand.errors import StateError
from ginstand.model.producer import Producer
from ginstand.store.book import Book
from ginstand.store.export import Written, read_back, tables, verify, write_all
from ginstand.store.migrations import MIGRATION_TABLE


@pytest.fixture
def stocked() -> Iterator[Book]:
    with Book.create(":memory:", date(2025, 8, 4)) as book:
        book.producers.add(Producer(ref="P-12", name="Aldys Brothers"))
        book.producers.add(Producer(ref="P-40", name="Merrick Land Co"))
        yield book


def test_the_tables_come_off_the_book_rather_than_a_list(stocked: Book) -> None:
    found = tables(stocked)
    assert "producer" in found
    assert "bale" in found
    assert MIGRATION_TABLE not in found
    assert "sqlite_sequence" not in found


def test_every_table_is_written_out(stocked: Book, tmp_path: Path) -> None:
    written = write_all(stocked, tmp_path / "out")
    assert len(written) == len(tables(stocked))
    for item in written:
        assert item.path.is_file()


def test_a_table_carries_a_header_row(stocked: Book, tmp_path: Path) -> None:
    write_all(stocked, tmp_path / "out")
    with (tmp_path / "out" / "producer.csv").open(newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[0] == ["ref", "name", "address", "phone", "ccc_number"]
    assert rows[1][0] == "P-12"
    assert len(rows) == 3


def test_the_row_count_leaves_the_header_out(stocked: Book, tmp_path: Path) -> None:
    written = {item.table: item for item in write_all(stocked, tmp_path / "out")}
    assert written["producer"].rows == 2
    assert written["bale"].rows == 0


def test_a_null_is_written_as_an_empty_cell(stocked: Book, tmp_path: Path) -> None:
    write_all(stocked, tmp_path / "out")
    with (tmp_path / "out" / "producer.csv").open(newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows[1][2] == ""


def test_the_folder_is_made_if_it_is_not_there(stocked: Book, tmp_path: Path) -> None:
    folder = tmp_path / "deep" / "out"
    write_all(stocked, folder)
    assert folder.is_dir()


def test_a_file_where_the_folder_should_be_is_refused(stocked: Book, tmp_path: Path) -> None:
    blocker = tmp_path / "out"
    blocker.write_text("in the way")
    with pytest.raises(StateError, match="is a file, not a folder"):
        write_all(stocked, blocker)


def test_a_clean_export_verifies(stocked: Book, tmp_path: Path) -> None:
    assert verify(write_all(stocked, tmp_path / "out")) == ()


def test_a_short_file_is_caught(stocked: Book, tmp_path: Path) -> None:
    written = write_all(stocked, tmp_path / "out")
    producer = next(item for item in written if item.table == "producer")
    producer.path.write_text("ref,name,address,phone,ccc_number\n")
    problems = verify(written)
    assert len(problems) == 1
    assert "has 0 rows and the export wrote 2" in problems[0]


def test_a_file_that_is_gone_is_refused(stocked: Book, tmp_path: Path) -> None:
    missing = Written(table="producer", path=tmp_path / "nothing.csv", rows=1)
    with pytest.raises(StateError, match="is not there"):
        read_back(missing)


def test_an_empty_file_reads_as_no_rows(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("")
    assert read_back(Written(table="x", path=path, rows=0)) == 0


def test_the_written_line_reads_as_a_report_row(stocked: Book, tmp_path: Path) -> None:
    written = {item.table: item for item in write_all(stocked, tmp_path / "out")}
    assert written["producer"].line.startswith("producer")
    assert written["producer"].line.endswith("producer.csv")


def test_a_decimal_survives_the_round_trip(tmp_path: Path) -> None:
    from ginstand.model.farm import Farm, Field
    from ginstand.model.producer import Lease, LeaseKind

    with Book.create(":memory:", date(2025, 8, 4)) as book:
        book.producers.add(Producer(ref="P-1", name="Aldys"))
        book.leases.add(Lease(ref="L-1", tenant="P-1", kind=LeaseKind.OWNER))
        book.farms.add(Farm(ref="F-1", producer="P-1", name="Home"))
        book.fields.add(
            Field(ref="FL-1", farm="F-1", name="North", acres=Decimal("78.40"), lease="L-1")
        )
        write_all(book, tmp_path / "out")
    with (tmp_path / "out" / "field.csv").open(newline="") as handle:
        rows = list(csv.reader(handle))
    assert "78.40" in rows[1]
