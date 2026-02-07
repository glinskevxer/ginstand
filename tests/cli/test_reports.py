"""The season and quality report commands."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import Result


def record(sequence: int, leaf: str = "3", colour: str = "31") -> str:
    return f"2541207{sequence:05d}20251022{colour}{leaf}34045270810000         MEM "


@pytest.fixture
def season(gin: Callable[..., Result]) -> Callable[..., Result]:
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
        "46140",
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
        "14",
    )
    gin("run", "seed", "GR-1", "--on", "2025-10-14", "--pounds", "9800")
    gin("run", "close", "GR-1", "--on", "2025-10-14", "--allocate")
    return gin


def class_all(season: Callable[..., Result], tmp_path: Path, leaf: str = "3") -> None:
    path = tmp_path / "cards.txt"
    path.write_text("\n".join(record(n, leaf) for n in range(1, 15)) + "\n")
    season("card", "file", str(path))


def test_the_season_summary_totals_the_year(season: Callable[..., Result]) -> None:
    output = season("report", "season", "--crop-year", "2025").output
    assert "Crop year 2025" in output
    assert "14 bales" in output
    assert "lint turnout" in output


def test_the_season_can_carry_the_run_and_producer_tables(
    season: Callable[..., Result],
) -> None:
    output = season("report", "season", "--crop-year", "2025", "--runs", "--producers").output
    assert "Runs in crop year 2025" in output
    assert "Producers in crop year 2025" in output


def test_a_crop_year_with_no_runs_is_refused(season: Callable[..., Result]) -> None:
    result = season("report", "season", "--crop-year", "2019")
    assert result.exit_code != 0
    assert "has no gin runs" in result.output


def test_the_run_table_prints_on_its_own(season: Callable[..., Result]) -> None:
    assert "GR-1" in season("report", "runs", "--crop-year", "2025").output


def test_the_producer_table_prints_on_its_own(season: Callable[..., Result]) -> None:
    assert "P-12" in season("report", "producers", "--crop-year", "2025").output


def test_the_quality_summary_needs_something_classed(
    season: Callable[..., Result],
) -> None:
    result = season("report", "quality", "--crop-year", "2025")
    assert result.exit_code != 0
    assert "has been classed" in result.output


def test_the_quality_summary_reads_the_averages(
    season: Callable[..., Result], tmp_path: Path
) -> None:
    class_all(season, tmp_path)
    output = season("report", "quality", "--crop-year", "2025").output
    assert "14 bales classed" in output
    assert "mic 4.50" in output


@pytest.mark.parametrize("table", ["colour", "staple", "off-schedule", "contamination"])
def test_every_quality_table_prints(
    season: Callable[..., Result], tmp_path: Path, table: str
) -> None:
    class_all(season, tmp_path)
    result = season("report", "quality", "--crop-year", "2025", "--table", table)
    assert result.exit_code == 0


def test_the_off_schedule_table_names_the_rule(
    season: Callable[..., Result], tmp_path: Path
) -> None:
    class_all(season, tmp_path, leaf="8")
    output = season("report", "quality", "--crop-year", "2025", "--table", "off-schedule").output
    assert "leaf below grade" in output
    assert "the office" in output


def test_the_book_report_counts_every_register(season: Callable[..., Result]) -> None:
    output = season("report", "book").output
    assert "producers  1" in output
    assert "bales      14" in output
    assert "14 bales waiting" in output


def test_the_audit_reads_the_whole_book(season: Callable[..., Result]) -> None:
    output = season("report", "audit", "--on", "2025-10-20").output
    assert "Book audit at 2025-10-20" in output
    assert "14 bales have no card yet" in output


def test_the_audit_can_be_narrowed_to_faults(season: Callable[..., Result]) -> None:
    assert "no faults" in season("report", "audit", "--on", "2025-10-20", "--faults-only").output


def test_a_closed_run_with_no_allocation_shows_as_a_fault(
    gin: Callable[..., Result],
) -> None:
    gin("producer", "add", "P-12", "Aldys Brothers")
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
        "46140",
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
    gin("run", "close", "GR-1", "--on", "2025-10-14")
    output = gin("report", "audit", "--on", "2025-10-20", "--faults-only").output
    assert "no allocation" in output
