"""The warehouse commands: adding houses, issuing receipts and billing storage."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import Result


@pytest.fixture
def stored(gin: Callable[..., Result]) -> Callable[..., Result]:
    gin("producer", "add", "P-12", "Aldys Brothers", "--ccc", "A4471")
    gin("producer", "add", "P-40", "Merrick Land Co")
    gin("lease", "add", "L-1", "P-12", "--kind", "owner")
    gin("farm", "add", "F-3", "P-12", "Home Place")
    gin("field", "add", "FL-9", "F-3", "North 80", "--acres", "78.4", "--lease", "L-1")
    gin(
        "yard",
        "receive",
        "M-1",
        "--field",
        "FL-9",
        "--harvested",
        "2025-09-28",
        "--received",
        "2025-10-02",
        "--gross",
        "48200",
        "--tare",
        "26140",
        "--moisture",
        "9.4",
        "--wrap",
        "tarp",
    )
    gin("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    gin("run", "feed", "GR-1", "M-1", "--on", "2025-10-14")
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
        "3",
    )
    gin("run", "close", "GR-1", "--on", "2025-10-14", "--allocate")
    gin("warehouse", "add", "WH-1", "Delta Compress", "--code", "41-207")
    return gin


def test_a_warehouse_is_added_and_says_if_it_is_licensed(
    stored: Callable[..., Result],
) -> None:
    assert "41-207" in stored("warehouse", "list").output
    assert "not licensed" in stored("warehouse", "add", "WH-2", "Gin yard shed").output
    assert (
        "(licensed)"
        in stored("warehouse", "add", "WH-3", "Bend Compress", "--code", "41-990").output
    )


def test_the_warehouse_list_counts_what_is_in_store(
    stored: Callable[..., Result],
) -> None:
    stored("receipt", "issue", "254120700001", "--warehouse", "WH-1", "--on", "2025-10-30")
    assert "1" in stored("warehouse", "list").output


def test_receipts_are_issued_with_numbers_from_the_book(
    stored: Callable[..., Result],
) -> None:
    result = stored(
        "receipt",
        "issue",
        "254120700001",
        "254120700002",
        "--warehouse",
        "WH-1",
        "--on",
        "2025-10-30",
    )
    assert result.exit_code == 0
    assert "WR-00001" in result.output
    assert "WR-00002" in result.output
    assert "P-12" in result.output


def test_a_bale_that_is_already_in_store_is_refused(
    stored: Callable[..., Result],
) -> None:
    stored("receipt", "issue", "254120700001", "--warehouse", "WH-1", "--on", "2025-10-30")
    result = stored("receipt", "issue", "254120700001", "--warehouse", "WH-1", "--on", "2025-10-31")
    assert result.exit_code != 0
    assert "already in store under receipt WR-00001" in result.output


def test_a_receipt_can_be_issued_to_somebody_else(stored: Callable[..., Result]) -> None:
    result = stored(
        "receipt",
        "issue",
        "254120700001",
        "--warehouse",
        "WH-1",
        "--on",
        "2025-10-30",
        "--holder",
        "P-40",
    )
    assert "P-40" in result.output


def test_a_receipt_can_be_released(stored: Callable[..., Result]) -> None:
    stored("receipt", "issue", "254120700001", "--warehouse", "WH-1", "--on", "2025-10-30")
    result = stored("receipt", "release", "WR-00001", "--on", "2026-01-30")
    assert result.exit_code == 0
    assert "after 92 days" in result.output


def test_releasing_twice_is_refused(stored: Callable[..., Result]) -> None:
    stored("receipt", "issue", "254120700001", "--warehouse", "WH-1", "--on", "2025-10-30")
    stored("receipt", "release", "WR-00001", "--on", "2026-01-30")
    result = stored("receipt", "release", "WR-00001", "--on", "2026-02-01")
    assert result.exit_code != 0
    assert "was released on 2026-01-30" in result.output


def test_a_receipt_can_be_transferred(stored: Callable[..., Result]) -> None:
    stored("receipt", "issue", "254120700001", "--warehouse", "WH-1", "--on", "2025-10-30")
    result = stored("receipt", "transfer", "WR-00001", "P-40")
    assert "now held by P-40" in result.output


def test_the_listing_shows_outstanding_receipts_by_default(
    stored: Callable[..., Result],
) -> None:
    stored("receipt", "issue", "254120700001", "--warehouse", "WH-1", "--on", "2025-10-30")
    stored("receipt", "release", "WR-00001", "--on", "2026-01-30")
    assert "nothing is in store" in stored("receipt", "list").output
    assert "WR-00001" in stored("receipt", "list", "--all").output


def test_the_listing_can_be_narrowed(stored: Callable[..., Result]) -> None:
    stored("receipt", "issue", "254120700001", "--warehouse", "WH-1", "--on", "2025-10-30")
    assert "WR-00001" in stored("receipt", "list", "--holder", "P-12").output
    assert "nothing is in store" in stored("receipt", "list", "--holder", "P-40").output
    assert "WR-00001" in stored("receipt", "list", "--warehouse", "WH-1").output


def test_storage_is_billed_against_the_years_contract(
    stored: Callable[..., Result],
) -> None:
    stored("receipt", "issue", "254120700001", "--warehouse", "WH-1", "--on", "2025-10-30")
    output = stored(
        "receipt", "storage", "P-12", "--on", "2026-01-30", "--crop-year", "2025"
    ).output
    assert "92" in output
    assert "82" in output
    assert "$9.66" in output


def test_a_crop_year_with_no_contract_is_refused(stored: Callable[..., Result]) -> None:
    result = stored("receipt", "storage", "P-12", "--on", "2026-01-30", "--crop-year", "2019")
    assert result.exit_code != 0
    assert "no storage contract is published" in result.output


def test_somebody_with_nothing_in_store_owes_nothing(
    stored: Callable[..., Result],
) -> None:
    output = stored(
        "receipt", "storage", "P-40", "--on", "2026-01-30", "--crop-year", "2025"
    ).output
    assert "nothing in store" in output


def test_the_receipt_file_prints(stored: Callable[..., Result]) -> None:
    stored("receipt", "issue", "254120700001", "--warehouse", "WH-1", "--on", "2025-10-30")
    output = stored("receipt", "export", "WH-1", "--on", "2025-10-30").output
    assert output.startswith("H41-207")
    assert "D254120700001" in output
    assert "T00001" in output


def test_the_receipt_file_can_be_written_out(stored: Callable[..., Result], tmp_path: Path) -> None:
    stored("receipt", "issue", "254120700001", "--warehouse", "WH-1", "--on", "2025-10-30")
    out = tmp_path / "ewr.txt"
    result = stored("receipt", "export", "WH-1", "--on", "2025-10-30", "--out", str(out))
    assert result.exit_code == 0
    assert "wrote 1 records" in result.output
    assert out.read_text().startswith("H41-207")


def test_an_unlicensed_warehouse_cannot_export(stored: Callable[..., Result]) -> None:
    stored("warehouse", "add", "WH-2", "Gin yard shed")
    result = stored("receipt", "export", "WH-2", "--on", "2025-10-30")
    assert result.exit_code != 0
    assert "no licensed code" in result.output


def test_the_position_prints_what_is_in_store(stored: Callable[..., Result]) -> None:
    assert "nothing is in store" in stored("warehouse", "position", "--on", "2026-01-30").output
    stored("receipt", "issue", "254120700001", "--warehouse", "WH-1", "--on", "2025-10-30")
    output = stored("warehouse", "position", "--on", "2026-01-30").output
    assert "In store at 2026-01-30" in output
    assert "WH-1" in output
    assert "P-12" in output


def test_a_warehouse_edit_can_licence_it(stored: Callable[..., Result]) -> None:
    stored("warehouse", "add", "WH-2", "Gin yard shed")
    result = stored("warehouse", "edit", "WH-2", "--code", "41-990")
    assert result.exit_code == 0
    assert "(licensed)" in result.output


def test_a_warehouse_edit_that_changes_nothing_says_so(
    stored: Callable[..., Result],
) -> None:
    assert "is unchanged" in stored("warehouse", "edit", "WH-1").output


def test_editing_a_warehouse_that_is_not_there_is_refused(
    stored: Callable[..., Result],
) -> None:
    result = stored("warehouse", "edit", "WH-9", "--name", "Nowhere")
    assert result.exit_code != 0
    assert "no warehouse with reference WH-9" in result.output
