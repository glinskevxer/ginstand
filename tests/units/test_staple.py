"""Staple is whole 32nds, and a fraction of a 32nd is refused rather than rounded."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ginstand.errors import ValidationError
from ginstand.units.staple import (
    LONGEST_STAPLE,
    SHORTEST_STAPLE,
    check_staple,
    format_staple,
    from_inches,
    parse_staple,
    to_inches,
)


def test_a_staple_in_range_passes_through() -> None:
    assert check_staple(34) == 34
    assert check_staple(SHORTEST_STAPLE) == SHORTEST_STAPLE
    assert check_staple(LONGEST_STAPLE) == LONGEST_STAPLE


def test_a_reading_off_the_bottom_is_not_upland_cotton() -> None:
    with pytest.raises(ValidationError, match="at least 24/32, got 23/32"):
        check_staple(23)


def test_a_reading_off_the_top_is_an_instrument_fault() -> None:
    with pytest.raises(ValidationError, match="no more than 48/32"):
        check_staple(49)


def test_a_float_staple_is_refused() -> None:
    with pytest.raises(ValidationError, match="whole number of 32nds"):
        check_staple(34.0)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("staple", "inches"),
    [(32, "1.0000"), (34, "1.0625"), (36, "1.1250"), (24, "0.7500"), (35, "1.0938")],
)
def test_the_inch_carries_four_places(staple: int, inches: str) -> None:
    assert to_inches(staple) == Decimal(inches)


def test_an_inch_converts_back_to_whole_32nds() -> None:
    assert from_inches(Decimal("1.0625")) == 34
    assert from_inches(Decimal("1")) == 32


def test_an_inch_that_is_not_a_whole_32nd_is_refused_not_rounded() -> None:
    with pytest.raises(ValidationError, match="not a whole 32nd"):
        from_inches(Decimal("1.05"))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("34", 34),
        (" 36 ", 36),
        ("34/32", 34),
        ("1.0625", 34),
        ("1.0625 in", 34),
        ('1.125"', 36),
        ("35/32", 35),
    ],
)
def test_a_staple_reads_off_a_card_however_it_was_written(text: str, expected: int) -> None:
    assert parse_staple(text) == expected


@pytest.mark.parametrize("text", ["", "  ", "long", "34.5", "1.05", "3/0"])
def test_a_staple_that_does_not_land_on_a_32nd_is_refused(text: str) -> None:
    with pytest.raises(ValidationError):
        parse_staple(text)


@pytest.mark.parametrize(
    ("staple", "printed"),
    [
        (34, "34 (1 2/32 in)"),
        (32, "32 (1 in)"),
        (24, "24 (24/32 in)"),
        (48, "48 (1 16/32 in)"),
    ],
)
def test_a_report_prints_the_32nds_then_the_inch(staple: int, printed: str) -> None:
    assert format_staple(staple) == printed
