"""References normalise, and the bale tag is built and read in one place."""

from __future__ import annotations

import pytest

from ginstand.errors import ValidationError
from ginstand.ids import MAX_BALE_SEQUENCE, Pbi, gin_code, make_pbi, parse_pbi, reference


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("p-12", "P-12"),
        (" GR-2025-04 ", "GR-2025-04"),
        ("M4471", "M4471"),
        ("ab", "AB"),
    ],
)
def test_a_reference_is_upper_cased_and_stripped(given: str, expected: str) -> None:
    assert reference(given) == expected


@pytest.mark.parametrize("given", ["", "  ", "A", "-P12", "P12-", "P 12", "P_12", "A" * 25])
def test_a_reference_that_will_not_key_a_record_is_refused(given: str) -> None:
    with pytest.raises(ValidationError):
        reference(given)


def test_a_reference_error_names_the_kind_it_was_asked_for() -> None:
    with pytest.raises(ValidationError, match="^producer:"):
        reference("", "producer")


def test_a_gin_code_is_exactly_five_digits() -> None:
    assert gin_code("41207") == "41207"
    assert gin_code(" 41207 ") == "41207"


@pytest.mark.parametrize("given", ["4120", "412071", "4120A", "", "-1207"])
def test_a_gin_code_of_the_wrong_shape_is_refused(given: str) -> None:
    with pytest.raises(ValidationError, match="must be 5 digits"):
        gin_code(given)


def test_a_bale_tag_is_the_crop_year_the_gin_and_the_sequence() -> None:
    tag = make_pbi(2025, "41207", 1)
    assert tag.tag == "254120700001"
    assert str(tag) == "254120700001"
    assert make_pbi(2026, "41207", 61).tag == "264120700061"


def test_the_sequence_is_padded_to_five_digits() -> None:
    assert make_pbi(2025, "41207", MAX_BALE_SEQUENCE).tag == "254120799999"


@pytest.mark.parametrize("year", [1999, 2100])
def test_a_crop_year_outside_the_two_digit_window_is_refused(year: int) -> None:
    with pytest.raises(ValidationError, match="between 2000 and 2099"):
        make_pbi(year, "41207", 1)


@pytest.mark.parametrize("sequence", [0, -1, MAX_BALE_SEQUENCE + 1])
def test_a_sequence_outside_the_issued_range_is_refused(sequence: int) -> None:
    with pytest.raises(ValidationError, match="bale sequence"):
        make_pbi(2025, "41207", sequence)


def test_a_bool_is_not_a_bale_sequence() -> None:
    with pytest.raises(ValidationError, match="whole number"):
        make_pbi(2025, "41207", True)


@pytest.mark.parametrize(
    "written",
    ["254120700061", " 254120700061 ", "25-41207-00061", "25 41207 00061"],
)
def test_a_tag_reads_however_the_document_grouped_it(written: str) -> None:
    assert parse_pbi(written) == Pbi(crop_year=2025, gin_code="41207", sequence=61)


def test_a_parsed_tag_round_trips_to_the_same_digits() -> None:
    assert parse_pbi("254120700061").tag == "254120700061"


@pytest.mark.parametrize("written", ["", "25412070006", "2541207000611", "2541207000AB"])
def test_a_tag_of_the_wrong_length_is_refused(written: str) -> None:
    with pytest.raises(ValidationError, match="must be 12 digits"):
        parse_pbi(written)


def test_sequence_zero_is_never_issued_so_it_reads_as_a_bad_tag() -> None:
    with pytest.raises(ValidationError, match="never issued"):
        parse_pbi("254120700000")


def test_a_tag_is_hashable_so_it_can_key_a_lookup() -> None:
    assert len({parse_pbi("254120700061"), make_pbi(2025, "41207", 61)}) == 1
