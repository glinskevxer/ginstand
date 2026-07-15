"""A day's file goes in, and the rows that will not are kept rather than fatal."""

from __future__ import annotations

import pytest

from ginstand.errors import ValidationError
from ginstand.store.book import Book
from ginstand.yard.intake import COLUMNS, parse_row, read

HEADER = ",".join(COLUMNS)


def a_row(tag: str = "M-1", **changes: str) -> str:
    fields = {
        "tag": tag,
        "field": "FL-9",
        "kind": "rectangular",
        "wrap": "tarp",
        "harvested": "2025-09-30",
        "received": "2025-10-02",
        "gross": "48200",
        "tare": "26140",
        "moisture": "9.4",
    }
    fields.update(changes)
    return ",".join(fields[column] for column in COLUMNS)


def a_file(*rows: str) -> str:
    return "\n".join([HEADER, *rows]) + "\n"


def test_a_file_with_no_header_is_refused(book: Book) -> None:
    with pytest.raises(ValidationError, match="has no header row"):
        read(book, "")


def test_a_file_missing_a_column_is_refused(book: Book) -> None:
    with pytest.raises(ValidationError, match="has no moisture column"):
        read(book, "tag,field,kind,wrap,harvested,received,gross,tare\n")


def test_a_days_file_weighs_everything_in(book: Book) -> None:
    intake = read(book, a_file(a_row("M-1"), a_row("M-2")))
    assert intake.clean
    assert len(intake.tickets) == 2
    assert intake.seed_cotton_pounds == 2 * 22_060
    assert book.modules.count() == 2


def test_the_summary_reads_as_one_line(book: Book) -> None:
    intake = read(book, a_file(a_row("M-1")))
    assert intake.summary == "1 modules in, 22,060 lb, 0 problems"


def test_a_row_that_will_not_go_in_is_kept(book: Book) -> None:
    intake = read(book, a_file(a_row("M-1"), a_row("M-2", field="FL-99")))
    assert len(intake.tickets) == 1
    assert len(intake.problems) == 1
    assert intake.problems[0].line_number == 3
    assert "no field with reference FL-99" in intake.problems[0].message
    assert not intake.clean


def test_the_good_rows_go_in_even_when_others_do_not(book: Book) -> None:
    read(book, a_file(a_row("M-1", field="FL-99"), a_row("M-2")))
    assert book.modules.exists("M-2")
    assert not book.modules.exists("M-1")


def test_a_repeated_tag_is_kept_as_a_problem(book: Book) -> None:
    intake = read(book, a_file(a_row("M-1"), a_row("M-1")))
    assert len(intake.tickets) == 1
    assert "already in the book" in intake.problems[0].message


@pytest.mark.parametrize(
    ("column", "value", "message"),
    [
        ("harvested", "30/09/2025", "must be an ISO date"),
        ("received", "not a date", "must be an ISO date"),
        ("gross", "48,200.5", "must be whole pounds"),
        ("tare", "heavy", "must be whole pounds"),
        ("moisture", "damp", "is not a number"),
    ],
)
def test_a_column_that_will_not_read_names_itself(
    book: Book, column: str, value: str, message: str
) -> None:
    intake = read(book, a_file(a_row("M-1", **{column: value})))
    assert len(intake.problems) == 1
    assert message in intake.problems[0].message
    assert intake.problems[0].tag == "M-1"


def test_a_kind_the_yard_does_not_have_is_kept_as_a_problem(book: Book) -> None:
    intake = read(book, a_file(a_row("M-1", kind="hexagonal")))
    assert len(intake.problems) == 1


def test_a_round_module_still_has_to_be_wrapped_in_film(book: Book) -> None:
    intake = read(book, a_file(a_row("M-1", kind="round", wrap="tarp")))
    assert "wrapped in film" in intake.problems[0].message


def test_a_row_with_a_column_missing_names_it() -> None:
    with pytest.raises(ValidationError, match="has no moisture in it"):
        parse_row({column: "x" for column in COLUMNS if column != "moisture"})


def test_a_file_with_only_a_header_takes_nothing_in(book: Book) -> None:
    intake = read(book, a_file())
    assert intake.tickets == ()
    assert intake.clean
    assert intake.seed_cotton_pounds == 0
