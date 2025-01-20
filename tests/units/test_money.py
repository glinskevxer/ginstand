"""Money is whole cents, rates carry four places, and rounding happens once."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ginstand.errors import ValidationError
from ginstand.units.money import (
    ZERO,
    Money,
    at_rate,
    format_money,
    format_rate,
    money,
    parse_money,
    rate,
    share_of,
    to_dollars,
)


def test_dollars_become_whole_cents() -> None:
    assert money("12.34") == 1234
    assert money(Decimal("0.07")) == 7
    assert money(0) == ZERO


def test_a_third_of_a_cent_rounds_half_up() -> None:
    assert money("0.005") == 1
    assert money("0.004") == 0
    assert money("-0.005") == -1


def test_a_non_number_is_refused_by_name() -> None:
    with pytest.raises(ValidationError, match="is not a number"):
        money("half a dollar")


def test_cents_read_back_as_dollars_with_two_places() -> None:
    assert to_dollars(Money(1234)) == Decimal("12.34")
    assert to_dollars(Money(-1234)) == Decimal("-12.34")
    assert str(to_dollars(Money(700))) == "7.00"


def test_a_rate_is_held_to_four_places() -> None:
    assert rate("52.00") == Decimal("52.0000")
    assert rate(Decimal("52.005")) == Decimal("52.0050")
    assert rate("52.00005") == Decimal("52.0001")


def test_a_rate_that_is_not_a_number_is_refused() -> None:
    with pytest.raises(ValidationError, match="is not a number"):
        rate("market")


def test_a_bale_is_valued_at_the_rate_in_cents_per_pound() -> None:
    assert at_rate(500, rate("52.00")) == 26_000
    assert format_money(at_rate(500, rate("52.00"))) == "$260.00"


def test_rounding_happens_once_at_the_end_not_per_pound() -> None:
    once = at_rate(487, rate("52.3456"))
    per_pound = 487 * int(Decimal("52.3456").quantize(Decimal("1")))
    assert once == 25_492
    assert once != per_pound


def test_a_negative_weight_has_no_value() -> None:
    with pytest.raises(ValidationError, match="must not be negative"):
        at_rate(-1, rate("52.00"))


def test_a_share_is_a_fraction_of_an_amount() -> None:
    assert share_of(Money(10_000), Decimal("0.25")) == 2_500
    assert share_of(Money(10_001), Decimal("0.25")) == 2_500
    assert share_of(Money(10_002), Decimal("0.25")) == 2_501


@pytest.mark.parametrize("fraction", [Decimal("-0.01"), Decimal("1.01")])
def test_a_share_outside_zero_to_one_is_refused(fraction: Decimal) -> None:
    with pytest.raises(ValidationError, match="between 0 and 1"):
        share_of(Money(100), fraction)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("12.34", 1234),
        ("$12.34", 1234),
        (" $1,234.56 ", 123_456),
        ("-12.34", -1234),
        ("(12.34)", -1234),
        ("($1,234.56)", -123_456),
        ("0", 0),
    ],
)
def test_an_amount_reads_off_a_statement_including_the_bracket_negative(
    text: str, expected: int
) -> None:
    assert parse_money(text) == expected


@pytest.mark.parametrize("text", ["", "   ", "$", "cheque"])
def test_an_amount_that_is_not_a_number_is_refused(text: str) -> None:
    with pytest.raises(ValidationError):
        parse_money(text)


@pytest.mark.parametrize(
    ("amount", "printed"),
    [
        (0, "$0.00"),
        (7, "$0.07"),
        (1234, "$12.34"),
        (123_456_789, "$1,234,567.89"),
        (-1234, "-$12.34"),
        (-7, "-$0.07"),
    ],
)
def test_a_statement_prints_the_sign_outside_the_dollar(amount: int, printed: str) -> None:
    assert format_money(Money(amount)) == printed


def test_a_schedule_prints_a_rate_to_two_places() -> None:
    assert format_rate(rate("52.0000")) == "52.00c"
    assert format_rate(rate("-1.2500")) == "-1.25c"
