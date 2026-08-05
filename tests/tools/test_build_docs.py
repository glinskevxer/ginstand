"""The command reference, and that the one on disk is still current."""

from __future__ import annotations

from pathlib import Path

import pytest

from ginstand.tools.base import repo_root
from ginstand.tools.build_docs import DOCUMENT, build, main
from ginstand.tools.check_help import command_names


def test_the_reference_on_disk_is_current() -> None:
    assert (repo_root() / DOCUMENT).read_text() == build()


def test_the_reference_check_passes_as_it_stands(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.argv", ["build_docs", "--check"])
    main()
    assert "build_docs: clean" in capsys.readouterr().out


def test_every_command_appears_in_the_reference() -> None:
    text = build()
    for name in command_names():
        words = name.split()[1:]
        assert f"ginstand {' '.join(words)}" in text


def test_a_group_gets_a_heading_and_no_usage_block() -> None:
    text = build()
    assert "## producer" in text
    assert "### producer add" in text
    assert "ginstand producer\n```" not in text


def test_the_arguments_are_shown_in_the_usage() -> None:
    text = build()
    assert "ginstand producer add <ref> <name>" in text
    assert "ginstand run feed <ref> <modules>..." in text


def test_the_options_are_listed_with_their_help() -> None:
    text = build()
    assert "- `--on` — the day the run opens (required)" in text
    assert "- `--shift` — which shift is on" in text


def test_the_reference_says_it_is_generated() -> None:
    assert "This file is generated" in build()


def test_the_reference_says_nothing_reads_the_clock() -> None:
    assert "Nothing reads the clock" in build()


def test_a_stale_reference_fails_the_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The check has to have been seen to fire, not only to pass."""
    (tmp_path / "docs").mkdir()
    (tmp_path / DOCUMENT).write_text("old\n")
    monkeypatch.setattr("ginstand.tools.build_docs.repo_root", lambda: tmp_path)
    monkeypatch.setattr("sys.argv", ["build_docs", "--check"])
    with pytest.raises(SystemExit) as exit_info:
        main()
    assert exit_info.value.code == 1
    assert "is out of date" in capsys.readouterr().out


def test_a_missing_reference_fails_the_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("ginstand.tools.build_docs.repo_root", lambda: tmp_path)
    monkeypatch.setattr("sys.argv", ["build_docs", "--check"])
    with pytest.raises(SystemExit) as exit_info:
        main()
    assert exit_info.value.code == 1
    assert "is not there" in capsys.readouterr().out


def test_writing_the_reference_makes_the_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("ginstand.tools.build_docs.repo_root", lambda: tmp_path)
    monkeypatch.setattr("sys.argv", ["build_docs"])
    main()
    assert (tmp_path / DOCUMENT).is_file()
    assert "wrote" in capsys.readouterr().out
