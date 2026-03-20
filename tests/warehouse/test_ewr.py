"""The receipt file, and the trailer that catches a truncated one."""

from __future__ import annotations

from datetime import date

import pytest

from ginstand.errors import StateError, ValidationError
from ginstand.model.warehouse import Warehouse
from ginstand.store.book import Book
from ginstand.warehouse.ewr import RECORD_WIDTH, build, check, lines_for, parse_detail
from ginstand.warehouse.receipts import issue, release

from .conftest import gin_a_run

ISSUED = date(2025, 10, 30)


def stored(book: Book, count: int = 3) -> None:
    gin_a_run(book, bales=count)
    for sequence in range(1, count + 1):
        issue(book, f"2541207{sequence:05d}", "WH-1", ISSUED)


def test_a_file_is_a_header_details_and_a_trailer(book: Book) -> None:
    stored(book)
    lines = build(book, "WH-1", ISSUED)
    assert lines[0].startswith("H")
    assert all(line.startswith("D") for line in lines[1:-1])
    assert lines[-1].startswith("T")
    assert len(lines) == 5


def test_every_record_is_the_same_width(book: Book) -> None:
    stored(book)
    for line in build(book, "WH-1", ISSUED):
        assert len(line) == RECORD_WIDTH


def test_a_detail_record_reads_back(book: Book) -> None:
    stored(book, 1)
    detail = build(book, "WH-1", ISSUED)[1]
    read = parse_detail(detail)
    assert read.tag == "254120700001"
    assert read.net_pounds == 490
    assert read.gin_code == "41207"
    assert read.pressed == date(2025, 10, 14)
    assert read.holder == "P-12"
    assert read.receipt == "WR-00001"


def test_something_that_is_not_a_detail_record_is_refused() -> None:
    with pytest.raises(ValidationError, match="is not a detail record"):
        parse_detail("H" + " " * 80)
    with pytest.raises(ValidationError, match="is not a detail record"):
        parse_detail("D123")


def test_the_trailer_carries_the_count_and_the_weight(book: Book) -> None:
    stored(book, 3)
    trailer = build(book, "WH-1", ISSUED)[-1]
    assert trailer[1:6] == "00003"
    assert int(trailer[6:15]) == 3 * 490


def test_a_whole_file_checks_out(book: Book) -> None:
    stored(book)
    text = "\n".join(build(book, "WH-1", ISSUED)) + "\n"
    details = check(text)
    assert len(details) == 3


def test_a_file_with_a_record_missing_is_refused(book: Book) -> None:
    stored(book)
    lines = list(build(book, "WH-1", ISSUED))
    del lines[2]
    with pytest.raises(ValidationError, match="says 3 records and the file carries 2"):
        check("\n".join(lines))


def test_a_file_whose_weights_do_not_add_up_is_refused(book: Book) -> None:
    stored(book)
    lines = list(build(book, "WH-1", ISSUED))
    lines[-1] = ("T" + "00003" + "000000001").ljust(len(lines[-1]))
    with pytest.raises(ValidationError, match="and the records add to"):
        check("\n".join(lines))


def test_a_file_with_no_header_is_refused(book: Book) -> None:
    stored(book)
    lines = list(build(book, "WH-1", ISSUED))[1:]
    with pytest.raises(ValidationError, match="no header and trailer"):
        check("\n".join(lines))


def test_an_unlicensed_warehouse_cannot_issue_receipts(book: Book) -> None:
    gin_a_run(book)
    book.warehouses.add(Warehouse(ref="WH-2", name="Gin yard shed"))
    with pytest.raises(StateError, match="has no licensed code"):
        build(book, "WH-2", ISSUED)


def test_a_released_bale_is_left_off_the_file(book: Book) -> None:
    stored(book, 2)
    release(book, "WR-00001", date(2026, 1, 30))
    assert [item.receipt for item in lines_for(book, "WH-1", ISSUED)] == ["WR-00002"]


def test_a_receipt_issued_after_the_file_day_is_left_off(book: Book) -> None:
    gin_a_run(book, bales=2)
    issue(book, "254120700001", "WH-1", ISSUED)
    issue(book, "254120700002", "WH-1", date(2025, 11, 4))
    assert len(lines_for(book, "WH-1", ISSUED)) == 1


def test_an_empty_warehouse_still_makes_a_file(book: Book) -> None:
    gin_a_run(book)
    lines = build(book, "WH-1", ISSUED)
    assert len(lines) == 2
    assert check("\n".join(lines)) == ()
