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


def test_the_recheck_report_says_when_nothing_has_been_asked(
    season: Callable[..., Result],
) -> None:
    output = season("report", "rechecks", "--on", "2025-11-03").output
    assert "no rechecks have been asked for" in output
    assert "days on average" not in output


def test_the_recheck_report_counts_the_outcomes(
    season: Callable[..., Result], tmp_path: Path
) -> None:
    class_all(season, tmp_path)
    season("recheck", "ask", "254120700001", "--reason", "leaf", "--on", "2025-10-27")
    season("recheck", "settle", "254120700001", "--outcome", "changed", "--on", "2025-11-03")
    output = season("report", "rechecks", "--on", "2025-11-03").output
    assert "Recheck outcomes" in output
    assert "leaf" in output
    assert "days on average" in output


def test_the_book_can_be_backed_up(season: Callable[..., Result], tmp_path: Path) -> None:
    target = tmp_path / "copy.sqlite3"
    result = season("book", "backup", str(target))
    assert result.exit_code == 0
    assert "backed" in result.output
    assert target.is_file()


def test_backing_up_over_something_is_refused(
    season: Callable[..., Result], tmp_path: Path
) -> None:
    target = tmp_path / "copy.sqlite3"
    target.write_text("in the way")
    result = season("book", "backup", str(target))
    assert result.exit_code != 0
    assert "is already there" in result.output


def test_a_sound_book_verifies(season: Callable[..., Result]) -> None:
    assert "the book is sound" in season("book", "verify").output


def test_the_counts_list_every_table(season: Callable[..., Result]) -> None:
    output = season("book", "counts").output
    assert "Rows in the book" in output
    assert "producer" in output
    assert "bale" in output


def test_the_book_can_be_compacted(season: Callable[..., Result]) -> None:
    result = season("book", "compact")
    assert result.exit_code == 0
    assert "bytes to" in result.output


def test_the_registers_export_as_csv(season: Callable[..., Result], tmp_path: Path) -> None:
    out = tmp_path / "csv"
    result = season("report", "export", str(out))
    assert result.exit_code == 0
    assert "tables," in result.output
    assert (out / "producer.csv").is_file()
    assert (out / "bale.csv").is_file()


def test_the_variety_report_prints(season: Callable[..., Result]) -> None:
    output = season("report", "varieties", "--crop-year", "2025").output
    assert "Varieties, crop year 2025" in output
    assert "unrecorded" in output


def test_the_plastic_report_says_when_there_is_none(
    season: Callable[..., Result],
) -> None:
    output = season("report", "plastic", "--crop-year", "2025").output
    assert "no bale came back with a plastic note" in output


def test_a_run_with_no_film_has_no_suspects(season: Callable[..., Result]) -> None:
    output = season("report", "suspects", "254120700001").output
    assert "no film wrapped module went into this bale's run" in output


def test_one_run_s_plastic_record_prints(season: Callable[..., Result]) -> None:
    output = season("report", "plastic", "--crop-year", "2025", "--run", "GR-1").output
    assert "GR-1  0/14 bales" in output


def test_an_instrument_is_added_with_its_interval(season: Callable[..., Result]) -> None:
    result = season("instrument", "add", "SC-1", "Weighbridge", "--kind", "truck scale")
    assert result.exit_code == 0
    assert "checked every 182 days" in result.output


def test_a_check_says_whether_it_passed(season: Callable[..., Result]) -> None:
    season("instrument", "add", "MM-1", "Yard meter", "--kind", "moisture meter")
    passed = season("instrument", "check", "MM-1", "--on", "2025-08-01", "--error", "0.2")
    assert "passed" in passed.output
    failed = season("instrument", "check", "MM-1", "--on", "2025-09-01", "--error", "2.4")
    assert "FAILED" in failed.output


def test_the_standing_names_the_ones_not_covered(
    season: Callable[..., Result],
) -> None:
    season("instrument", "add", "SC-1", "Weighbridge", "--kind", "truck scale")
    assert "never" in season("instrument", "standing", "--on", "2025-10-14").output
    season("instrument", "check", "SC-1", "--on", "2025-08-01", "--error", "12")
    assert (
        "every instrument is covered"
        in season("instrument", "standing", "--on", "2025-10-14").output
    )


def test_one_instrument_can_be_asked_about(season: Callable[..., Result]) -> None:
    season("instrument", "add", "SC-1", "Weighbridge", "--kind", "truck scale")
    season("instrument", "check", "SC-1", "--on", "2025-08-01", "--error", "12")
    output = season("instrument", "standing", "--on", "2025-10-14", "--ref", "SC-1").output
    assert "covered" in output
    assert "due 2026-01-30" in output


def test_the_unvouched_tickets_are_listed(season: Callable[..., Result]) -> None:
    season("instrument", "add", "SC-1", "Weighbridge", "--kind", "truck scale")
    assert "1 tickets" in season("instrument", "unvouched", "SC-1").output
    season("instrument", "check", "SC-1", "--on", "2025-08-01", "--error", "12")
    assert (
        "every ticket was written on a vouched scale"
        in season("instrument", "unvouched", "SC-1").output
    )


def test_the_day_sheet_prints(season: Callable[..., Result]) -> None:
    output = season("report", "day", "--on", "2025-10-14").output
    assert "Day sheet for 2025-10-14" in output
    assert "pressed" in output


def test_a_quiet_day_says_so(season: Callable[..., Result]) -> None:
    output = season("report", "day", "--on", "2025-12-25").output
    assert "nothing was written down for this day" in output


def test_the_day_sheet_can_carry_its_lists(season: Callable[..., Result]) -> None:
    output = season("report", "day", "--on", "2025-10-14", "--lists").output
    assert "Pressed on 2025-10-14" in output


def test_the_book_check_prints_one_page(season: Callable[..., Result]) -> None:
    output = season("book", "check", "--on", "2025-10-20").output
    assert "Book check at 2025-10-20" in output
    assert "schema version" in output
    assert "queries" in output


def test_the_moisture_report_carries_both_turnouts(
    season: Callable[..., Result],
) -> None:
    output = season("report", "moisture", "--crop-year", "2025").output
    assert "dry turnout" in output
    assert "GR-1" in output


def test_one_run_s_moisture_prints(season: Callable[..., Result]) -> None:
    output = season("report", "moisture", "--crop-year", "2025", "--run", "GR-1").output
    assert output.startswith("GR-1  in ")
    assert "gap" in output
