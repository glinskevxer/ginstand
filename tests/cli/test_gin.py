"""The gin commands: opening, feeding, pressing, closing and allocating."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from click.testing import Result


@pytest.fixture
def gin_yard(gin: Callable[..., Result]) -> Callable[..., Result]:
    gin("producer", "add", "P-12", "Aldys Brothers")
    gin("producer", "add", "P-40", "Merrick Land Co")
    gin("lease", "add", "L-1", "P-12", "--kind", "owner")
    gin("lease", "add", "L-3", "P-40", "--kind", "owner")
    gin("farm", "add", "F-3", "P-12", "Home Place")
    gin("farm", "add", "F-7", "P-40", "River Place")
    gin("field", "add", "FL-9", "F-3", "North 80", "--acres", "78.4", "--lease", "L-1")
    gin("field", "add", "FL-5", "F-7", "Bend", "--acres", "55", "--lease", "L-3")
    for tag, field_ref in (("M-1", "FL-9"), ("M-2", "FL-5")):
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
            "48200",
            "--tare",
            "26140",
            "--moisture",
            "9.4",
            "--wrap",
            "tarp",
        )
    return gin


def test_a_run_opens_under_the_right_crop_year(gin_yard: Callable[..., Result]) -> None:
    result = gin_yard("run", "open", "gr-1", "--gin-code", "41207", "--on", "2025-10-14")
    assert result.exit_code == 0
    assert "GR-1 for crop year 2025" in result.output


def test_a_second_open_run_is_refused(gin_yard: Callable[..., Result]) -> None:
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    result = gin_yard("run", "open", "GR-2", "--gin-code", "41207", "--on", "2025-10-15")
    assert result.exit_code != 0
    assert "GR-1 is still open" in result.output


def test_modules_feed_in_the_order_given(gin_yard: Callable[..., Result]) -> None:
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    result = gin_yard("run", "feed", "GR-1", "M-2", "M-1", "--on", "2025-10-14")
    assert result.exit_code == 0
    assert result.output.splitlines()[0].strip().startswith("1  M-2")
    assert result.output.splitlines()[1].strip().startswith("2  M-1")


def test_feeding_a_held_module_is_refused(gin_yard: Callable[..., Result]) -> None:
    gin_yard("yard", "hold", "M-1", "--reason", "wet", "--on", "2025-10-03")
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    result = gin_yard("run", "feed", "GR-1", "M-1", "--on", "2025-10-14")
    assert result.exit_code != 0
    assert "held for wet" in result.output


def test_the_queue_can_be_fed_straight_in(gin_yard: Callable[..., Result]) -> None:
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    result = gin_yard("run", "feed-queue", "GR-1", "--on", "2025-10-14")
    assert result.exit_code == 0
    assert "M-1" in result.output
    assert "M-2" in result.output


def test_the_queue_feed_can_be_limited(gin_yard: Callable[..., Result]) -> None:
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    result = gin_yard("run", "feed-queue", "GR-1", "--on", "2025-10-14", "--limit", "1")
    assert len(result.output.strip().splitlines()) == 1


def test_an_empty_queue_says_so(gin_yard: Callable[..., Result]) -> None:
    gin_yard("yard", "hold", "M-1", "--reason", "wet", "--on", "2025-10-03")
    gin_yard("yard", "hold", "M-2", "--reason", "wet", "--on", "2025-10-03")
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    assert (
        "nothing is free to gin"
        in gin_yard("run", "feed-queue", "GR-1", "--on", "2025-10-14").output
    )


def press_some(gin_yard: Callable[..., Result], count: int = 4) -> Result:
    return gin_yard(
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
        str(count),
    )


def test_bales_come_off_the_press_numbered(gin_yard: Callable[..., Result]) -> None:
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    gin_yard("run", "feed", "GR-1", "M-1", "--on", "2025-10-14")
    result = press_some(gin_yard, 2)
    assert "254120700001" in result.output
    assert "254120700002" in result.output
    assert "490 lb" in result.output


def test_a_bale_above_the_storage_ceiling_is_refused(
    gin_yard: Callable[..., Result],
) -> None:
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    gin_yard("run", "feed", "GR-1", "M-1", "--on", "2025-10-14")
    result = gin_yard(
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
        "8.2",
    )
    assert result.exit_code != 0
    assert "will heat in the warehouse" in result.output


def test_the_restoration_ceiling_can_be_asked_for(gin_yard: Callable[..., Result]) -> None:
    result = gin_yard("run", "restore", "--pressed", "490", "--from", "5.0")
    assert result.exit_code == 0
    assert "may be taken to" in result.output


def test_closing_can_allocate_in_the_same_step(gin_yard: Callable[..., Result]) -> None:
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    gin_yard("run", "feed", "GR-1", "M-1", "M-2", "--on", "2025-10-14")
    press_some(gin_yard)
    result = gin_yard("run", "close", "GR-1", "--on", "2025-10-14", "--allocate")
    assert result.exit_code == 0
    assert "closed gin run GR-1" in result.output
    assert "P-12" in result.output
    assert "P-40" in result.output


def test_closing_an_empty_run_is_refused(gin_yard: Callable[..., Result]) -> None:
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    result = gin_yard("run", "close", "GR-1", "--on", "2025-10-14")
    assert result.exit_code != 0
    assert "has nothing in it" in result.output


def test_the_allocation_can_be_worked_out_without_writing_it(
    gin_yard: Callable[..., Result],
) -> None:
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    gin_yard("run", "feed", "GR-1", "M-1", "M-2", "--on", "2025-10-14")
    press_some(gin_yard)
    gin_yard("run", "close", "GR-1", "--on", "2025-10-14")
    dry = gin_yard("run", "allocate", "GR-1", "--on", "2025-10-14", "--dry-run")
    assert dry.exit_code == 0
    assert "P-12" in dry.output
    wet = gin_yard("run", "allocate", "GR-1", "--on", "2025-10-14")
    assert "Gin run GR-1 allocation" in wet.output


def test_seed_loads_are_booked_and_totalled(gin_yard: Callable[..., Result]) -> None:
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    gin_yard("run", "feed", "GR-1", "M-1", "--on", "2025-10-14")
    first = gin_yard("run", "seed", "GR-1", "--on", "2025-10-14", "--pounds", "9800")
    assert "9,800 lb of seed" in first.output
    second = gin_yard("run", "seed", "GR-1", "--on", "2025-10-15", "--pounds", "1200")
    assert "11,000 lb of seed on this run so far" in second.output


def test_the_run_sheet_prints_the_three_tables(gin_yard: Callable[..., Result]) -> None:
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    gin_yard("run", "feed", "GR-1", "M-1", "--on", "2025-10-14")
    press_some(gin_yard)
    output = gin_yard("run", "sheet", "GR-1").output
    assert "feed sheet" in output
    assert "GR-1 bales" in output
    assert "GR-1 allocation" in output


def test_the_sheet_can_be_narrowed(gin_yard: Callable[..., Result]) -> None:
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    gin_yard("run", "feed", "GR-1", "M-1", "--on", "2025-10-14")
    press_some(gin_yard)
    assert "GR-1 bales" not in gin_yard("run", "sheet", "GR-1", "--feed-only").output
    assert "feed sheet" not in gin_yard("run", "sheet", "GR-1", "--bales-only").output


def test_the_current_run_can_be_asked_for(gin_yard: Callable[..., Result]) -> None:
    assert "no gin run is open" in gin_yard("run", "current").output
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    gin_yard("run", "feed", "GR-1", "M-1", "--on", "2025-10-14")
    assert "GR-1 opened 2025-10-14, 1 modules" in gin_yard("run", "current").output


def test_pressing_nothing_says_so(gin_yard: Callable[..., Result]) -> None:
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    gin_yard("run", "feed", "GR-1", "M-1", "--on", "2025-10-14")
    assert "nothing to press" in press_some(gin_yard, 0).output


def test_the_weights_command_reads_the_run(gin_yard: Callable[..., Result]) -> None:
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    gin_yard("run", "feed", "GR-1", "M-1", "--on", "2025-10-14")
    press_some(gin_yard, 6)
    output = gin_yard("run", "weights", "GR-1").output
    assert "GR-1  6 bales  mean 490.0" in output
    assert "measured against" in output


def test_a_run_with_no_bales_has_no_weights(gin_yard: Callable[..., Result]) -> None:
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    result = gin_yard("run", "weights", "GR-1")
    assert result.exit_code != 0
    assert "has pressed no bales" in result.output


def test_the_press_control_lists_the_season(gin_yard: Callable[..., Result]) -> None:
    assert (
        "no run in this crop year has pressed a bale"
        in gin_yard("run", "press-control", "--crop-year", "2025").output
    )
    gin_yard("run", "open", "GR-1", "--gin-code", "41207", "--on", "2025-10-14")
    gin_yard("run", "feed", "GR-1", "M-1", "--on", "2025-10-14")
    press_some(gin_yard, 6)
    assert "GR-1" in gin_yard("run", "press-control", "--crop-year", "2025").output
