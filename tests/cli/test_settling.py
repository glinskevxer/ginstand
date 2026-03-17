"""The settlement commands: a statement, the register and the check."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import Result


def record(sequence: int, leaf: str = "3") -> str:
    return f"2541207{sequence:05d}2025102231{leaf}34045270810000         MEM "


@pytest.fixture
def settled(gin: Callable[..., Result], tmp_path: Path) -> Callable[..., Result]:
    gin("producer", "add", "P-12", "Aldys Brothers", "--ccc", "A4471")
    gin("producer", "add", "P-40", "Merrick Land Co", "--ccc", "M2210")
    gin("lease", "add", "L-1", "P-12", "--kind", "owner")
    gin("lease", "add", "L-3", "P-40", "--kind", "owner")
    gin("farm", "add", "F-3", "P-12", "Home Place")
    gin("farm", "add", "F-7", "P-40", "River Place")
    gin("field", "add", "FL-9", "F-3", "North 80", "--acres", "78.4", "--lease", "L-1")
    gin("field", "add", "FL-5", "F-7", "Bend", "--acres", "55", "--lease", "L-3")
    for tag, field_ref, gross in (("M-1", "FL-9", 46_140), ("M-2", "FL-5", 36_140)):
        gin(
            "yard",
            "receive",
            tag,
            "--field",
            field_ref,
            "--harvested",
            "2025-09-28",
            "--received",
            "2025-10-02",
            "--gross",
            str(gross),
            "--tare",
            "26140",
            "--moisture",
            "9.4",
            "--wrap",
            "tarp",
        )
    gin("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    gin("run", "feed", "GR-1", "M-1", "M-2", "--on", "2025-10-14")
    gin(
        "run",
        "press",
        "GR-1",
        "--on",
        "2025-10-14",
        "--gross",
        "512",
        "--tare",
        "22",
        "--moisture",
        "6.8",
        "--count",
        "8",
    )
    gin("run", "seed", "GR-1", "--on", "2025-10-14", "--pounds", "14000")
    gin("run", "close", "GR-1", "--on", "2025-10-14", "--allocate")
    return gin


def class_all(settled: Callable[..., Result], tmp_path: Path) -> None:
    path = tmp_path / "cards.txt"
    path.write_text("\n".join(record(n) for n in range(1, 9)) + "\n")
    settled("card", "file", str(path))


def test_the_shares_list_before_any_money(settled: Callable[..., Result]) -> None:
    output = settled("settle", "shares", "GR-1").output
    assert "P-12" in output
    assert "P-40" in output
    assert "L-1" in output


def test_a_statement_prints_for_one_producer(settled: Callable[..., Result]) -> None:
    output = settled("settle", "statement", "GR-1", "P-12", "--on", "2025-11-03").output
    assert "Gin run GR-1   P-12" in output
    assert "seed credit" in output
    assert "charges" in output
    assert "total" in output


def test_a_statement_before_the_cards_is_marked_provisional(
    settled: Callable[..., Result],
) -> None:
    output = settled("settle", "statement", "GR-1", "P-12", "--on", "2025-11-03").output
    assert "PROVISIONAL" in output


def test_a_classed_statement_is_not_provisional(
    settled: Callable[..., Result], tmp_path: Path
) -> None:
    class_all(settled, tmp_path)
    output = settled("settle", "statement", "GR-1", "P-12", "--on", "2025-11-03").output
    assert "PROVISIONAL" not in output


def test_an_optional_charge_can_be_asked_for(settled: Callable[..., Result]) -> None:
    plain = settled("settle", "statement", "GR-1", "P-12", "--on", "2025-11-03").output
    extra = settled(
        "settle", "statement", "GR-1", "P-12", "--on", "2025-11-03", "--extra", "REST"
    ).output
    assert plain != extra


def test_a_charge_code_that_is_not_on_the_tariff_is_refused(
    settled: Callable[..., Result],
) -> None:
    result = settled("settle", "statement", "GR-1", "P-12", "--on", "2025-11-03", "--extra", "NOPE")
    assert result.exit_code != 0
    assert "not on the 2025 tariff" in result.output


def test_the_register_lists_everybody(settled: Callable[..., Result]) -> None:
    output = settled("settle", "register", "GR-1", "--on", "2025-11-03").output
    assert "Settlement register" in output
    assert "P-12" in output
    assert "P-40" in output


def test_the_check_reconciles_a_classed_run(settled: Callable[..., Result], tmp_path: Path) -> None:
    class_all(settled, tmp_path)
    output = settled("settle", "check", "GR-1", "--on", "2025-11-03").output
    assert "GR-1 reconciles" in output


def test_the_check_names_provisional_producers(settled: Callable[..., Result]) -> None:
    output = settled("settle", "check", "GR-1", "--on", "2025-11-03").output
    assert "provisional for" in output


def test_settling_a_producer_who_is_not_on_the_run_is_refused(
    settled: Callable[..., Result],
) -> None:
    settled("producer", "add", "P-99", "Nobody")
    result = settled("settle", "statement", "GR-1", "P-99", "--on", "2025-11-03")
    assert result.exit_code != 0
    assert "has nothing on gin run GR-1" in result.output


def test_the_tariff_prints_with_the_seed_price(settled: Callable[..., Result]) -> None:
    output = settled("settle", "tariff", "--crop-year", "2025").output
    assert "Ginning tariff, crop year 2025" in output
    assert "on request" in output
    assert "cottonseed $210.00 a ton" in output


def test_a_crop_year_with_no_tariff_is_refused(settled: Callable[..., Result]) -> None:
    result = settled("settle", "tariff", "--crop-year", "2019")
    assert result.exit_code != 0
    assert "no ginning tariff is published" in result.output


def test_the_account_is_empty_until_something_is_posted(
    settled: Callable[..., Result],
) -> None:
    output = settled("account", "show", "P-12", "--crop-year", "2025").output
    assert "nothing has been posted to this account" in output


def test_a_provisional_statement_cannot_be_posted(
    settled: Callable[..., Result],
) -> None:
    result = settled("account", "post", "GR-1", "P-12", "--on", "2025-11-03")
    assert result.exit_code != 0
    assert "is provisional" in result.output


def test_posting_a_settlement_moves_the_balance(
    settled: Callable[..., Result], tmp_path: Path
) -> None:
    class_all(settled, tmp_path)
    result = settled("account", "post", "GR-1", "P-12", "--on", "2025-11-03")
    assert result.exit_code == 0
    assert "posted" in result.output
    assert "balance" in result.output


def test_posting_the_same_run_twice_is_refused(
    settled: Callable[..., Result], tmp_path: Path
) -> None:
    class_all(settled, tmp_path)
    settled("account", "post", "GR-1", "P-12", "--on", "2025-11-03")
    again = settled("account", "post", "GR-1", "P-12", "--on", "2025-11-04")
    assert again.exit_code != 0
    assert "was already settled for GR-1" in again.output


def an_adjustment(settled: Callable[..., Result], amount: str = "-40.00") -> Result:
    return settled(
        "account",
        "adjust",
        "P-12",
        "--amount",
        amount,
        "--crop-year",
        "2025",
        "--on",
        "2025-11-10",
        "--reason",
        "module weight corrected",
    )


def a_payment(settled: Callable[..., Result], amount: str = "100.00") -> Result:
    return settled(
        "account",
        "pay",
        "P-12",
        "--amount",
        amount,
        "--crop-year",
        "2025",
        "--on",
        "2025-11-12",
        "--reference",
        "CHQ-4471",
    )


def test_an_adjustment_moves_the_balance(settled: Callable[..., Result], tmp_path: Path) -> None:
    class_all(settled, tmp_path)
    settled("account", "post", "GR-1", "P-12", "--on", "2025-11-03")
    result = an_adjustment(settled)
    assert result.exit_code == 0
    assert "module weight corrected" in result.output
    assert "-$40.00" in result.output


def test_a_payment_is_typed_the_way_the_cheque_reads(
    settled: Callable[..., Result], tmp_path: Path
) -> None:
    class_all(settled, tmp_path)
    settled("account", "post", "GR-1", "P-12", "--on", "2025-11-03")
    result = a_payment(settled)
    assert result.exit_code == 0
    assert "paid $100.00 to P-12" in result.output


def test_a_payment_over_the_balance_is_refused(
    settled: Callable[..., Result], tmp_path: Path
) -> None:
    class_all(settled, tmp_path)
    settled("account", "post", "GR-1", "P-12", "--on", "2025-11-03")
    result = a_payment(settled, "999999.00")
    assert result.exit_code != 0
    assert "is owed" in result.output


def test_an_amount_that_is_not_a_number_is_refused(
    settled: Callable[..., Result], tmp_path: Path
) -> None:
    class_all(settled, tmp_path)
    result = an_adjustment(settled, "lots")
    assert result.exit_code != 0
    assert "is not an amount" in result.output


def test_the_account_shows_every_entry_with_a_balance(
    settled: Callable[..., Result], tmp_path: Path
) -> None:
    class_all(settled, tmp_path)
    settled("account", "post", "GR-1", "P-12", "--on", "2025-11-03")
    an_adjustment(settled)
    a_payment(settled)
    output = settled("account", "show", "P-12", "--crop-year", "2025").output
    assert "settlement" in output
    assert "adjustment" in output
    assert "payment" in output
    assert "balance" in output


def test_the_owing_list_names_the_producers_still_owed(
    settled: Callable[..., Result], tmp_path: Path
) -> None:
    class_all(settled, tmp_path)
    settled("account", "post", "GR-1", "P-12", "--on", "2025-11-03")
    settled("account", "post", "GR-1", "P-40", "--on", "2025-11-03")
    output = settled("account", "owing", "--crop-year", "2025").output
    assert "Aldys Brothers" in output
    assert "Merrick Land Co" in output


def test_a_crop_year_with_no_accounts_is_square(
    settled: Callable[..., Result],
) -> None:
    assert "every account is square" in settled("account", "owing", "--crop-year", "2026").output
