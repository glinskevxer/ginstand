"""The file is fixed width with implied decimals, and one bad record is not fatal."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.classing.ingest import parse_record, read
from ginstand.errors import ValidationError
from ginstand.grades.color import ColorGrade

RECORD = "2541207000612025102231335043294812006BK1      MEM "
LONGER = RECORD + "reclass requested"


def test_a_record_reads_into_a_card() -> None:
    card = parse_record(RECORD)
    assert card.tag == "254120700061"
    assert card.classed == date(2025, 10, 22)
    assert card.color == ColorGrade(31)
    assert card.leaf == 3
    assert card.staple == 35
    assert card.office == "MEM"


def test_the_implied_decimal_place_is_put_back() -> None:
    card = parse_record(RECORD)
    assert card.micronaire == Decimal("4.3")
    assert card.strength == Decimal("29.4")
    assert card.uniformity == Decimal("81.2")
    assert card.trash_pct == Decimal("0.6")


def test_the_extraneous_block_reads_up_to_three_notes() -> None:
    card = parse_record(RECORD)
    assert [note.code for note in card.extraneous] == ["BK1"]
    two = RECORD[:37] + "BK2PL1   " + RECORD[46:]
    assert [note.code for note in parse_record(two).extraneous] == ["BK2", "PL1"]


def test_a_record_with_no_notes_reads_with_none() -> None:
    blank = RECORD[:37] + "         " + RECORD[46:]
    assert parse_record(blank).extraneous == ()


def test_the_remarks_run_to_the_end_of_the_line() -> None:
    assert parse_record(LONGER).remarks == "reclass requested"
    assert parse_record(RECORD).remarks == ""


def test_a_short_record_is_refused_with_its_length() -> None:
    with pytest.raises(ValidationError, match="is 20 characters, expected at least 50"):
        parse_record(RECORD[:20])


@pytest.mark.parametrize(
    ("position", "replacement", "message"),
    [
        (12, "2025X022", "classed"),
        (20, "XX", "colour grade"),
        (22, "X", "leaf grade"),
        (23, "XX", "staple"),
        (25, "XXX", "micronaire"),
        (28, "XXX", "strength"),
        (31, "XXX", "uniformity"),
        (34, "XXX", "trash"),
    ],
)
def test_a_field_that_is_not_digits_is_refused_by_name(
    position: int, replacement: str, message: str
) -> None:
    spoiled = RECORD[:position] + replacement + RECORD[position + len(replacement) :]
    with pytest.raises(ValidationError, match=message):
        parse_record(spoiled)


def test_a_grade_that_is_not_on_the_chart_is_refused() -> None:
    spoiled = RECORD[:20] + "14" + RECORD[22:]
    with pytest.raises(ValidationError, match="not a square on the chart"):
        parse_record(spoiled)


def test_a_tag_that_is_not_twelve_digits_is_refused() -> None:
    spoiled = "25412070006A" + RECORD[12:]
    with pytest.raises(ValidationError, match="must be 12 digits"):
        parse_record(spoiled)


def test_a_whole_file_reads() -> None:
    second = RECORD[:11] + "2" + RECORD[12:]
    reading = read(f"{RECORD}\n{second}\n")
    assert len(reading.cards) == 2
    assert reading.clean
    assert reading.summary == "2 cards read, 0 problems"


def test_blank_lines_are_skipped() -> None:
    reading = read(f"\n{RECORD}\n\n   \n")
    assert len(reading.cards) == 1
    assert reading.clean


def test_one_unreadable_record_does_not_stop_the_read() -> None:
    second = RECORD[:11] + "2" + RECORD[12:]
    reading = read(f"{RECORD}\nrubbish\n{second}\n")
    assert len(reading.cards) == 2
    assert len(reading.problems) == 1
    assert reading.problems[0].line_number == 2
    assert not reading.clean


def test_a_problem_names_its_line_and_what_was_wrong() -> None:
    reading = read(f"{RECORD}\n{RECORD[:20]}\n")
    assert reading.problems[0].line == "line 2: record: is 20 characters, expected at least 50"
    assert reading.problems[0].text == RECORD[:20]


def test_an_empty_file_reads_as_nothing() -> None:
    reading = read("")
    assert reading.cards == ()
    assert reading.clean
    assert reading.summary == "0 cards read, 0 problems"
