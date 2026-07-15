"""The yard commands: weighing in, holding, and the two listings."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import Result


@pytest.fixture
def yard(gin: Callable[..., Result]) -> Callable[..., Result]:
    gin("producer", "add", "P-12", "Aldys Brothers")
    gin("lease", "add", "L-1", "P-12", "--kind", "owner")
    gin("farm", "add", "F-3", "P-12", "Home Place")
    gin("field", "add", "FL-9", "F-3", "North 80", "--acres", "78.4", "--lease", "L-1")
    return gin


def weigh_in(yard: Callable[..., Result], tag: str, **options: str) -> Result:
    args = [
        "yard",
        "receive",
        tag,
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
    ]
    for key, value in options.items():
        flag = f"--{key.replace('_', '-')}"
        if flag in args:
            args[args.index(flag) + 1] = value
        else:
            args.extend([flag, value])
    return yard(*args)


def test_a_module_can_be_weighed_in(yard: Callable[..., Result]) -> None:
    result = weigh_in(yard, "M-1")
    assert result.exit_code == 0
    assert "Aldys Brothers" in result.output
    assert "22,060 lb" in result.output


def test_a_wet_module_is_flagged_on_the_ticket(yard: Callable[..., Result]) -> None:
    assert "WET" in weigh_in(yard, "M-1", moisture="12.5").output


def test_a_very_wet_module_suggests_a_hold(yard: Callable[..., Result]) -> None:
    assert "suggest holding for wet" in weigh_in(yard, "M-1", moisture="15.0").output


def test_a_module_on_a_field_that_is_not_there_is_refused(
    yard: Callable[..., Result],
) -> None:
    result = weigh_in(yard, "M-1", field="FL-99")
    assert result.exit_code != 0
    assert "no field with reference FL-99" in result.output


def test_a_round_module_must_be_wrapped_in_film(yard: Callable[..., Result]) -> None:
    result = weigh_in(yard, "M-1", kind="round", wrap="tarp")
    assert result.exit_code != 0
    assert "wrapped in film" in result.output


def test_show_reads_the_module_and_where_it_stands(yard: Callable[..., Result]) -> None:
    weigh_in(yard, "M-1", moisture="12.0")
    output = yard("yard", "show", "m-1", "--on", "2025-10-12").output
    assert "M-1" in output
    assert "10 days in the yard" in output
    assert "not ginned" in output


def test_an_at_risk_module_is_marked_on_show(yard: Callable[..., Result]) -> None:
    weigh_in(yard, "M-1", moisture="14.0")
    assert "AT RISK" in yard("yard", "show", "M-1", "--on", "2025-10-12").output


def test_a_module_can_be_held_and_lifted(yard: Callable[..., Result]) -> None:
    weigh_in(yard, "M-1")
    held = yard("yard", "hold", "M-1", "--reason", "plastic", "--on", "2025-10-03", "--by", "RE")
    assert held.exit_code == 0
    assert "held M-1 for plastic" in held.output
    lifted = yard("yard", "lift", "M-1", "--on", "2025-10-09", "--by", "JP")
    assert lifted.exit_code == 0
    assert "after 6 days" in lifted.output


def test_holding_a_module_twice_is_refused(yard: Callable[..., Result]) -> None:
    weigh_in(yard, "M-1")
    yard("yard", "hold", "M-1", "--reason", "wet", "--on", "2025-10-03")
    result = yard("yard", "hold", "M-1", "--reason", "plastic", "--on", "2025-10-04")
    assert result.exit_code != 0
    assert "already held for wet" in result.output


def test_lifting_a_module_that_is_not_held_is_refused(yard: Callable[..., Result]) -> None:
    weigh_in(yard, "M-1")
    result = yard("yard", "lift", "M-1", "--on", "2025-10-09")
    assert result.exit_code != 0
    assert "is not held" in result.output


def test_the_standing_lists_the_yard(yard: Callable[..., Result]) -> None:
    weigh_in(yard, "M-1")
    output = yard("yard", "standing", "--on", "2025-10-12").output
    assert "Module yard standing" in output
    assert "M-1" in output


def test_the_queue_leaves_out_what_is_held(yard: Callable[..., Result]) -> None:
    weigh_in(yard, "M-1")
    weigh_in(yard, "M-2")
    yard("yard", "hold", "M-1", "--reason", "wet", "--on", "2025-10-03")
    output = yard("yard", "queue", "--on", "2025-10-12").output
    assert "M-2" in output
    assert "M-1" not in output


def test_the_queue_can_be_run_ungrouped(yard: Callable[..., Result]) -> None:
    weigh_in(yard, "M-1")
    assert yard("yard", "queue", "--on", "2025-10-12", "--no-group").exit_code == 0


def test_the_hold_list_names_who_placed_it(yard: Callable[..., Result]) -> None:
    weigh_in(yard, "M-1")
    yard("yard", "hold", "M-1", "--reason", "weight", "--on", "2025-10-03", "--by", "R Ellis")
    output = yard("yard", "holds", "--on", "2025-10-12").output
    assert "R Ellis" in output
    assert "weight" in output


def test_an_empty_yard_says_so(yard: Callable[..., Result]) -> None:
    assert "the yard is empty" in yard("yard", "standing", "--on", "2025-10-12").output


def test_a_module_stands_in_a_row_and_comes_out_again(
    yard: Callable[..., Result],
) -> None:
    weigh_in(yard, "M-1")
    placed = yard("yard", "put", "M-1", "a", "--on", "2025-10-02")
    assert placed.exit_code == 0
    assert "M-1 is at A-01" in placed.output
    cleared = yard("yard", "clear", "M-1")
    assert "has come out of A-01" in cleared.output


def test_the_map_shows_the_rows(yard: Callable[..., Result]) -> None:
    assert "nothing has been placed in the yard" in yard("yard", "map").output
    weigh_in(yard, "M-1")
    weigh_in(yard, "M-2")
    yard("yard", "put", "M-1", "A", "--on", "2025-10-02")
    yard("yard", "put", "M-2", "A", "--on", "2025-10-02")
    output = yard("yard", "map").output
    assert "row A: 2 modules" in output
    assert "A-01  M-1" in output


def test_digging_says_what_is_in_front(yard: Callable[..., Result]) -> None:
    weigh_in(yard, "M-1")
    weigh_in(yard, "M-2")
    assert "not on the yard map" in yard("yard", "dig", "M-1").output
    yard("yard", "put", "M-1", "A", "--on", "2025-10-02")
    yard("yard", "put", "M-2", "A", "--on", "2025-10-02")
    assert "1 modules in front of it" in yard("yard", "dig", "M-1").output
    assert "at the open end of A" in yard("yard", "dig", "M-2").output


def test_the_feed_order_counts_what_is_out_of_place(
    yard: Callable[..., Result],
) -> None:
    assert "nothing is free to gin" in yard("yard", "feed-order", "--on", "2025-10-12").output
    weigh_in(yard, "M-1", moisture="13.0")
    weigh_in(yard, "M-2", moisture="7.0")
    yard("yard", "put", "M-1", "A", "--on", "2025-10-02")
    yard("yard", "put", "M-2", "A", "--on", "2025-10-02")
    output = yard("yard", "feed-order", "--on", "2025-10-12").output
    assert "2 modules, 2 out of the order the cotton wants" in output


def test_a_days_file_is_weighed_in(yard: Callable[..., Result], tmp_path: Path) -> None:
    header = "tag,field,kind,wrap,harvested,received,gross,tare,moisture"
    row = "{},FL-9,rectangular,tarp,2025-09-30,2025-10-02,48200,26140,9.4"
    path = tmp_path / "scale.csv"
    path.write_text("\n".join([header, row.format("M-1"), row.format("M-2")]) + "\n")
    result = yard("yard", "intake", str(path))
    assert result.exit_code == 0
    assert "2 modules in, 44,120 lb, 0 problems" in result.output


def test_the_intake_can_print_a_line_per_module(
    yard: Callable[..., Result], tmp_path: Path
) -> None:
    header = "tag,field,kind,wrap,harvested,received,gross,tare,moisture"
    row = "M-1,FL-9,rectangular,tarp,2025-09-30,2025-10-02,48200,26140,9.4"
    path = tmp_path / "scale.csv"
    path.write_text(f"{header}\n{row}\n")
    output = yard("yard", "intake", str(path), "--tickets").output
    assert "Aldys Brothers" in output


def test_a_row_that_will_not_go_in_is_printed(yard: Callable[..., Result], tmp_path: Path) -> None:
    header = "tag,field,kind,wrap,harvested,received,gross,tare,moisture"
    row = "M-1,FL-99,rectangular,tarp,2025-09-30,2025-10-02,48200,26140,9.4"
    path = tmp_path / "scale.csv"
    path.write_text(f"{header}\n{row}\n")
    output = yard("yard", "intake", str(path)).output
    assert "1 problems" in output
    assert "no field with reference FL-99" in output


def test_a_file_with_no_header_is_refused(yard: Callable[..., Result], tmp_path: Path) -> None:
    path = tmp_path / "scale.csv"
    path.write_text("")
    result = yard("yard", "intake", str(path))
    assert result.exit_code != 0
    assert "has no header row" in result.output
