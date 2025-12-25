"""The smoke walk, run against the source tree as well as the wheel."""

from __future__ import annotations

from pathlib import Path

import pytest

from ginstand.tools.smoke import main, walk


def test_the_walk_runs_a_season_through(tmp_path: Path) -> None:
    lines = walk(tmp_path / "smoke.sqlite3")
    assert "registers stood up" in lines
    assert any("34 bales" in line for line in lines)
    assert any(line.startswith("34 filed") for line in lines)


def test_the_walk_leaves_a_book_behind_it(tmp_path: Path) -> None:
    path = tmp_path / "smoke.sqlite3"
    walk(path)
    assert path.is_file()


def test_the_walk_reports_the_statement_and_the_receipt(tmp_path: Path) -> None:
    lines = walk(tmp_path / "smoke.sqlite3")
    assert any("statement 34 bales" in line for line in lines)
    assert any("receipt WR-00001 issued to P-12" in line for line in lines)


def test_running_it_as_a_module_prints_clean(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main()
    assert "smoke: clean" in capsys.readouterr().out


def test_the_quiet_form_prints_only_the_verdict(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.argv", ["smoke", "--quiet"])
    main()
    output = capsys.readouterr().out
    assert output.strip() == "smoke: clean"
