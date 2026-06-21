"""The loan commands: one bale, a lot, the tables and the register."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import Result


def record(sequence: int = 1, leaf: str = "3", colour: str = "31") -> str:
    return f"2541207{sequence:05d}20251022{colour}{leaf}34045270810000         MEM "


@pytest.fixture
def valued(gin: Callable[..., Result], tmp_path: Path) -> Callable[..., Result]:
    gin("producer", "add", "P-12", "Aldys Brothers", "--ccc", "A4471")
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
        "2",
    )
    gin("run", "close", "GR-1", "--on", "2025-10-14", "--allocate")
    path = tmp_path / "cards.txt"
    path.write_text(f"{record(1)}\n{record(2)}\n")
    gin("card", "file", str(path))
    return gin


def test_one_bale_is_valued_at_the_base_rate(valued: Callable[..., Result]) -> None:
    output = valued("loan", "value", "254120700001").output
    assert "490 lb at 52.00c" in output
    assert "$254.80" in output


def test_the_working_can_be_printed(valued: Callable[..., Result]) -> None:
    output = valued("loan", "value", "254120700001", "--working").output
    assert "base" in output
    assert "colour" in output
    assert "micronaire" in output
    assert "rate" in output


def test_a_bale_with_no_card_cannot_be_valued(valued: Callable[..., Result]) -> None:
    result = valued("loan", "value", "254120700099")
    assert result.exit_code != 0


def test_a_lot_is_valued_for_a_producer(valued: Callable[..., Result]) -> None:
    output = valued("loan", "lot", "P-12", "--crop-year", "2025").output
    assert "Aldys Brothers" in output
    assert "2 bales" in output
    assert "average 52.00c" in output


def test_a_producer_with_nothing_classed_says_so(valued: Callable[..., Result]) -> None:
    valued("producer", "add", "P-40", "Merrick Land Co")
    output = valued("loan", "lot", "P-40", "--crop-year", "2025").output
    assert "no classed bales in crop year 2025" in output


def test_a_refused_bale_is_counted_on_the_lot(
    valued: Callable[..., Result], tmp_path: Path
) -> None:
    path = tmp_path / "recheck.txt"
    path.write_text(f"{record(1, leaf='8')}\n")
    valued("card", "file", str(path), "--recheck")
    output = valued("loan", "lot", "P-12", "--crop-year", "2025").output
    assert "1 refused: leaf below grade" in output


def test_the_colour_table_prints(valued: Callable[..., Result]) -> None:
    output = valued("loan", "schedule", "--crop-year", "2025").output
    assert "Colour points, crop year 2025" in output
    assert "base 52.00c" in output
    assert "31" in output


def test_the_staple_table_prints_both_ladders(valued: Callable[..., Result]) -> None:
    output = valued("loan", "schedule", "--crop-year", "2025", "--table", "staple").output
    assert "White And Light Spotted" in output.title()
    assert "Spotted And Worse" in output.title()


def test_the_mic_table_shows_the_premium_band(valued: Callable[..., Result]) -> None:
    output = valued("loan", "schedule", "--crop-year", "2025", "--table", "mic").output
    assert "premium range" in output
    assert "125" in output


@pytest.mark.parametrize("table", ["leaf", "strength", "uniformity"])
def test_every_schedule_table_prints_on_its_own(valued: Callable[..., Result], table: str) -> None:
    result = valued("loan", "schedule", "--crop-year", "2025", "--table", table)
    assert result.exit_code == 0


def test_a_crop_year_with_no_schedule_is_refused(valued: Callable[..., Result]) -> None:
    result = valued("loan", "schedule", "--crop-year", "2019")
    assert result.exit_code != 0
    assert "no loan schedule is loaded" in result.output


def test_the_register_totals_the_crop_year(valued: Callable[..., Result]) -> None:
    output = valued("loan", "register", "--crop-year", "2025").output
    assert "Loan register, crop year 2025" in output
    assert "$509.60" in output


def test_an_unclassed_crop_year_register_says_so(valued: Callable[..., Result]) -> None:
    output = valued("loan", "register", "--crop-year", "2026").output
    assert "nothing has been classed in this crop year" in output
