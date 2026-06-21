"""The classing commands: filing a file, reading a card, and the gin's own estimate."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import Result


def record(sequence: int = 1, classed: str = "20251022", leaf: str = "3") -> str:
    return f"2541207{sequence:05d}{classed}31{leaf}35043294812006BK1      MEM "


@pytest.fixture
def ginned(gin: Callable[..., Result]) -> Callable[..., Result]:
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
    return gin


def test_a_classing_file_files(ginned: Callable[..., Result], tmp_path: Path) -> None:
    path = tmp_path / "cards.txt"
    path.write_text(f"{record(1)}\n{record(2)}\n")
    result = ginned("card", "file", str(path))
    assert result.exit_code == 0
    assert "2 cards read, 0 problems" in result.output
    assert "2 filed, 0 replaced, 0 rejected" in result.output


def test_a_dry_run_reads_without_filing(ginned: Callable[..., Result], tmp_path: Path) -> None:
    path = tmp_path / "cards.txt"
    path.write_text(f"{record(1)}\n")
    ginned("card", "file", str(path), "--dry-run")
    assert "nothing has been classed" in ginned("card", "list").output


def test_an_unreadable_record_is_reported_with_its_line(
    ginned: Callable[..., Result], tmp_path: Path
) -> None:
    path = tmp_path / "cards.txt"
    path.write_text(f"{record(1)}\nrubbish\n")
    output = ginned("card", "file", str(path)).output
    assert "1 cards read, 1 problems" in output
    assert "line 2" in output


def test_a_card_for_a_bale_nobody_pressed_is_rejected(
    ginned: Callable[..., Result], tmp_path: Path
) -> None:
    path = tmp_path / "cards.txt"
    path.write_text(f"{record(999)}\n")
    output = ginned("card", "file", str(path)).output
    assert "0 filed" in output
    assert "no bale in the book carries this tag" in output


def test_a_recheck_replaces_a_card(ginned: Callable[..., Result], tmp_path: Path) -> None:
    first = tmp_path / "first.txt"
    first.write_text(f"{record(1)}\n")
    ginned("card", "file", str(first))
    second = tmp_path / "second.txt"
    second.write_text(f"{record(1, classed='20251103', leaf='5')}\n")
    plain = ginned("card", "file", str(second))
    assert "0 filed, 0 replaced, 1 rejected" in plain.output
    recheck = ginned("card", "file", str(second), "--recheck")
    assert "0 filed, 1 replaced, 0 rejected" in recheck.output


def test_show_reads_the_whole_card(ginned: Callable[..., Result], tmp_path: Path) -> None:
    path = tmp_path / "cards.txt"
    path.write_text(f"{record(1)}\n")
    ginned("card", "file", str(path))
    output = ginned("card", "show", "254120700001").output
    assert "Middling White" in output
    assert "on schedule" in output
    assert "off run GR-1" in output


def test_showing_a_bale_with_no_card_says_so(ginned: Callable[..., Result]) -> None:
    result = ginned("card", "show", "254120700001")
    assert result.exit_code != 0
    assert "no classing card" in result.output


def test_the_card_list_can_be_narrowed_to_a_run(
    ginned: Callable[..., Result], tmp_path: Path
) -> None:
    path = tmp_path / "cards.txt"
    path.write_text(f"{record(1)}\n")
    ginned("card", "file", str(path))
    assert "254120700001" in ginned("card", "list", "--run", "GR-1").output
    assert "nothing has been classed" in ginned("card", "list", "--run", "GR-9").output


def test_the_outstanding_list_counts_what_is_waiting(
    ginned: Callable[..., Result], tmp_path: Path
) -> None:
    assert "3 bales waiting" in ginned("card", "outstanding").output
    path = tmp_path / "cards.txt"
    path.write_text(f"{record(1)}\n{record(2)}\n{record(3)}\n")
    ginned("card", "file", str(path))
    assert "every bale has been classed" in ginned("card", "outstanding").output


def test_the_estimate_says_it_is_only_an_estimate(ginned: Callable[..., Result]) -> None:
    output = ginned("card", "estimate", "--rd", "70.0", "--plus-b", "8.0").output
    assert "Middling White" in output
    assert "the card is what counts" in output


def test_an_estimate_off_the_instrument_range_is_refused(
    ginned: Callable[..., Result],
) -> None:
    result = ginned("card", "estimate", "--rd", "30.0", "--plus-b", "8.0")
    assert result.exit_code != 0
    assert "Rd" in result.output


def a_carded_book(ginned: Callable[..., Result], tmp_path: Path) -> None:
    path = tmp_path / "cards.txt"
    path.write_text(f"{record(1)}\n")
    ginned("card", "file", str(path))


def test_a_recheck_can_be_asked_for(ginned: Callable[..., Result], tmp_path: Path) -> None:
    a_carded_book(ginned, tmp_path)
    result = ginned(
        "recheck",
        "ask",
        "254120700001",
        "--reason",
        "colour",
        "--on",
        "2025-10-27",
        "--by",
        "R Ellis",
    )
    assert result.exit_code == 0
    assert "sent on 254120700001 for colour" in result.output


def test_a_recheck_on_an_unclassed_bale_is_refused(
    ginned: Callable[..., Result],
) -> None:
    result = ginned("recheck", "ask", "254120700001", "--reason", "colour", "--on", "2025-10-27")
    assert result.exit_code != 0
    assert "nothing to recheck" in result.output


def test_a_recheck_past_the_window_is_refused(
    ginned: Callable[..., Result], tmp_path: Path
) -> None:
    a_carded_book(ginned, tmp_path)
    result = ginned("recheck", "ask", "254120700001", "--reason", "colour", "--on", "2025-12-01")
    assert result.exit_code != 0
    assert "only held to" in result.output


def test_the_open_list_shows_the_days_out(ginned: Callable[..., Result], tmp_path: Path) -> None:
    a_carded_book(ginned, tmp_path)
    ginned("recheck", "ask", "254120700001", "--reason", "leaf", "--on", "2025-10-27")
    output = ginned("recheck", "list", "--on", "2025-11-03").output
    assert "254120700001" in output
    assert "leaf" in output
    assert "7" in output


def test_the_chase_list_is_narrower(ginned: Callable[..., Result], tmp_path: Path) -> None:
    a_carded_book(ginned, tmp_path)
    ginned("recheck", "ask", "254120700001", "--reason", "leaf", "--on", "2025-10-27")
    assert "nothing is out" in ginned("recheck", "list", "--on", "2025-11-03", "--chase").output
    assert "254120700001" in ginned("recheck", "list", "--on", "2025-11-20", "--chase").output


def test_a_recheck_can_be_answered_by_hand(ginned: Callable[..., Result], tmp_path: Path) -> None:
    a_carded_book(ginned, tmp_path)
    ginned("recheck", "ask", "254120700001", "--reason", "leaf", "--on", "2025-10-27")
    result = ginned(
        "recheck", "settle", "254120700001", "--outcome", "refused", "--on", "2025-11-03"
    )
    assert "came back refused after 7 days" in result.output
    assert "nothing is out" in ginned("recheck", "list", "--on", "2025-11-03").output


def test_filing_a_recheck_card_closes_it_as_changed(
    ginned: Callable[..., Result], tmp_path: Path
) -> None:
    a_carded_book(ginned, tmp_path)
    ginned("recheck", "ask", "254120700001", "--reason", "leaf", "--on", "2025-10-27")
    second = tmp_path / "second.txt"
    second.write_text(f"{record(1, classed='20251103', leaf='2')}\n")
    ginned("card", "file", str(second), "--recheck")
    output = ginned("recheck", "history", "254120700001").output
    assert "changed" in output
    assert "leaf 3 to 2" in output


def test_a_bale_never_rechecked_says_so(ginned: Callable[..., Result]) -> None:
    assert "never been rechecked" in ginned("recheck", "history", "254120700001").output
