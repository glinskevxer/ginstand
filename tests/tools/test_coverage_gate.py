"""The coverage gate, and the two floors it holds."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ginstand.tools.coverage_gate import FileCoverage, failures, main, read_report


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


def test_one_bad_file_is_caught_behind_a_good_total() -> None:
    files = (FileCoverage("a.py", 99.0, 1), FileCoverage("b.py", 9.0, 40))
    problems = list(failures(95.0, files, 90.0, 70.0))
    assert len(problems) == 1
    assert "b.py is 9.00%" in problems[0]
    assert "40 lines uncovered" in problems[0]


def test_every_failure_is_reported_not_just_the_first() -> None:
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
