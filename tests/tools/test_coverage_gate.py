"""The coverage gate, and the two floors it holds."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ginstand.tools.coverage_gate import (
    FileCoverage,
    failures,
    main,
    read_report,
    worst,
)


def a_report(tmp_path: Path, total: float, files: dict[str, float]) -> Path:
    path = tmp_path / "coverage.json"
    path.write_text(
        json.dumps(
            {
                "totals": {"percent_covered": total},
                "files": {
                    name: {"summary": {"percent_covered": percent, "missing_lines": 3}}
                    for name, percent in files.items()
                },
            }
        )
    )
    return path


def test_a_report_reads_back(tmp_path: Path) -> None:
    path = a_report(tmp_path, 95.5, {"a.py": 99.0, "b.py": 80.0})
    total, files = read_report(path)
    assert total == 95.5
    assert [item.path for item in files] == ["a.py", "b.py"]
    assert files[0].missing == 3


def test_a_report_over_both_floors_is_clean() -> None:
    files = (FileCoverage("a.py", 99.0, 1), FileCoverage("b.py", 80.0, 4))
    assert list(failures(95.0, files, 90.0, 70.0)) == []


def test_a_total_under_the_floor_is_reported() -> None:
    problems = list(failures(85.0, (), 90.0, 70.0))
    assert len(problems) == 1
    assert "coverage is 85.00%" in problems[0]


def test_one_thin_file_is_caught_behind_a_healthy_total() -> None:
    files = (FileCoverage("a.py", 99.0, 1), FileCoverage("b.py", 9.0, 40))
    problems = list(failures(95.0, files, 90.0, 70.0))
    assert len(problems) == 1
    assert "b.py is 9.00%" in problems[0]
    assert "40 lines uncovered" in problems[0]


def test_every_shortfall_is_reported_not_just_the_first() -> None:
    files = (FileCoverage("a.py", 10.0, 1), FileCoverage("b.py", 9.0, 40))
    assert len(list(failures(50.0, files, 90.0, 70.0))) == 3


def test_a_missing_report_fails_by_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["coverage_gate", "--report", str(tmp_path / "nothing.json")])
    with pytest.raises(SystemExit) as exit_info:
        main()
    assert exit_info.value.code == 1
    assert "there is no report at" in capsys.readouterr().out


def test_a_clean_report_passes_the_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = a_report(tmp_path, 98.0, {"a.py": 99.0})
    monkeypatch.setattr("sys.argv", ["coverage_gate", "--report", str(path)])
    main()
    assert "clean at 98.00%" in capsys.readouterr().out


def test_a_report_under_the_floor_exits_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = a_report(tmp_path, 50.0, {"a.py": 20.0})
    monkeypatch.setattr("sys.argv", ["coverage_gate", "--report", str(path)])
    with pytest.raises(SystemExit) as exit_info:
        main()
    assert exit_info.value.code == 1
    assert "coverage_gate: 2 problems" in capsys.readouterr().out


def test_the_floors_the_workflow_sets_are_the_ones_the_package_clears() -> None:
    """A floor above where the package sits gets lowered, and stops meaning anything."""
    from ginstand.tools.base import repo_root

    workflow = (repo_root() / ".github" / "workflows" / "ci.yml").read_text()
    assert "coverage_gate --floor 96 --file-floor 85 --worst 5" in workflow


def test_the_defaults_agree_with_the_workflow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = a_report(tmp_path, 96.0, {"a.py": 85.0})
    monkeypatch.setattr("sys.argv", ["coverage_gate", "--report", str(path)])
    main()
    assert "clean at 96.00%" in capsys.readouterr().out


def test_a_file_just_under_the_default_file_floor_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = a_report(tmp_path, 99.0, {"a.py": 84.9})
    monkeypatch.setattr("sys.argv", ["coverage_gate", "--report", str(path)])
    with pytest.raises(SystemExit):
        main()


def test_the_least_covered_files_come_back_worst_first() -> None:
    files = (
        FileCoverage("a.py", 99.0, 1),
        FileCoverage("b.py", 60.0, 40),
        FileCoverage("c.py", 80.0, 10),
    )
    assert [item.path for item in worst(files, 2)] == ["b.py", "c.py"]


def test_asking_for_none_of_the_worst_gives_none() -> None:
    files = (FileCoverage("a.py", 99.0, 1),)
    assert worst(files, 0) == ()


def test_asking_for_more_than_there_are_gives_what_there_is() -> None:
    files = (FileCoverage("a.py", 99.0, 1),)
    assert len(worst(files, 10)) == 1


def test_two_files_at_the_same_cover_sort_by_name() -> None:
    files = (FileCoverage("b.py", 90.0, 1), FileCoverage("a.py", 90.0, 1))
    assert [item.path for item in worst(files, 2)] == ["a.py", "b.py"]


def test_the_worst_files_print_even_when_the_gate_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = a_report(tmp_path, 99.0, {"a.py": 99.0, "b.py": 90.0})
    monkeypatch.setattr("sys.argv", ["coverage_gate", "--report", str(path), "--worst", "1"])
    main()
    output = capsys.readouterr().out
    assert "90.00%  b.py" in output
    assert "clean at" in output


def test_the_worst_files_print_when_the_gate_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    path = a_report(tmp_path, 50.0, {"a.py": 20.0})
    monkeypatch.setattr("sys.argv", ["coverage_gate", "--report", str(path), "--worst", "1"])
    with pytest.raises(SystemExit):
        main()
    output = capsys.readouterr().out
    assert "20.00%  a.py" in output
    assert "3 lines uncovered" in output
