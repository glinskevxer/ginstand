"""Weights are whole pounds, and the ways a ticket goes wrong are named."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ginstand.errors import ValidationError
from ginstand.units.weight import (
    MAX_TICKET_POUNDS,
    check_pounds,
    format_pounds,
    from_cwt,
    net_of,
    parse_pounds,
    to_cwt,
)


def test_a_plain_weight_passes_through_unchanged() -> None:
    assert check_pounds(21_450, "gross weight") == 21_450
    assert check_pounds(0, "tare weight") == 0


def test_a_bool_is_not_a_weight() -> None:
    with pytest.raises(ValidationError, match="whole number of pounds"):
        check_pounds(True, "gross weight")


def test_a_float_is_not_a_weight_even_when_it_is_whole() -> None:
    with pytest.raises(ValidationError, match="whole number of pounds"):
        check_pounds(21450.0, "gross weight")  # type: ignore[arg-type]


def test_the_bounds_are_named_in_the_message() -> None:
    with pytest.raises(ValidationError, match="at least 0 lb, got -1"):
        check_pounds(-1, "tare weight")
    with pytest.raises(ValidationError, match="no more than 200000 lb"):
        check_pounds(MAX_TICKET_POUNDS + 1, "gross weight")


def test_a_caller_can_raise_the_floor_for_a_field_that_cannot_be_empty() -> None:
    assert check_pounds(400, "bale weight", minimum=200) == 400
    with pytest.raises(ValidationError, match="at least 200 lb"):
        check_pounds(199, "bale weight", minimum=200)


def test_net_is_gross_less_tare() -> None:
    assert net_of(48_200, 26_140) == 22_060


def test_a_tare_heavier_than_the_gross_reads_as_a_reversed_ticket() -> None:
    with pytest.raises(ValidationError, match="check the ticket"):
        net_of(26_140, 48_200)


def test_an_equal_gross_and_tare_is_an_empty_load_not_an_error() -> None:
    assert net_of(26_140, 26_140) == 0


@pytest.mark.parametrize(
    ("pounds", "expected"),
    [
        (0, "0.00"),
        (100, "1.00"),
        (22_060, "220.60"),
        (5, "0.05"),
        (1_005, "10.05"),
    ],
)
def test_hundredweight_carries_two_places(pounds: int, expected: str) -> None:
    assert to_cwt(pounds) == Decimal(expected)


def test_hundredweight_rounds_half_up_at_the_last_place() -> None:
    assert to_cwt(1_235) == Decimal("12.35")
    assert to_cwt(1_234) == Decimal("12.34")


def test_hundredweight_converts_back_to_whole_pounds() -> None:
    assert from_cwt(Decimal("220.60")) == 22_060
    assert from_cwt(Decimal("12.345")) == 1_235
    assert from_cwt(Decimal("0")) == 0


def test_a_negative_hundredweight_is_refused() -> None:
    with pytest.raises(ValidationError, match="must not be negative"):
        from_cwt(Decimal("-1"))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("22060", 22_060),
        (" 22,060 ", 22_060),
        ("22060 lb", 22_060),
        ("22,060 LBS", 22_060),
        ("0", 0),
    ],
)
def test_a_weight_copied_off_a_printout_still_reads(text: str, expected: int) -> None:
    assert parse_pounds(text) == expected


@pytest.mark.parametrize("text", ["", "   ", "heavy", "22.5", "1e4"])
def test_a_weight_that_is_not_a_whole_number_is_refused(text: str) -> None:
    with pytest.raises(ValidationError):
        parse_pounds(text)


def test_a_parsed_weight_is_bounds_checked_like_any_other() -> None:
    with pytest.raises(ValidationError, match="no more than"):
        parse_pounds("999,999")


def test_a_report_prints_a_thousands_separator() -> None:
    assert format_pounds(22_060) == "22,060 lb"
    assert format_pounds(0) == "0 lb"
