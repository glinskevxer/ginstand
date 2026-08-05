"""The pin check, and the project passing it."""

from __future__ import annotations

from pathlib import Path

import pytest

from ginstand.tools.check_pins import (
    PIN,
    closure,
    constraints_file,
    direct_pins,
    findings,
    project_file,
    unpinned,
)


def test_every_dependency_is_pinned_and_agrees_with_the_closure() -> None:
    assert list(findings()) == []


def test_nothing_in_the_project_is_left_unpinned() -> None:
    assert list(unpinned()) == []


def test_the_direct_pins_read_off_the_project_file() -> None:
    pins = direct_pins()
    assert pins["click"] == "8.1.8"
    assert pins["pytest"] == "8.3.4"
    assert pins["ruff"] == "0.9.2"
    assert pins["mypy"] == "1.14.1"


def test_the_closure_covers_every_direct_pin() -> None:
    pins = direct_pins()
    closed = closure()
    for name, version in pins.items():
        assert closed[name] == version


def test_the_closure_carries_more_than_the_direct_pins() -> None:
    assert set(closure()) > set(direct_pins())
    assert "pluggy" in closure()


def test_both_files_are_where_the_check_looks() -> None:
    assert project_file().is_file()
    assert constraints_file().is_file()


def test_the_pin_pattern_takes_a_version_and_refuses_a_range() -> None:
    assert PIN.match("click==8.1.8")
    assert PIN.match("pytest-cov==6.0.0")
    assert not PIN.match("click>=8.0")
    assert not PIN.match("click")
    assert not PIN.match("click~=8.1")


def test_the_stack_is_an_early_2025_one() -> None:
    closed = closure()
    assert closed["coverage"].startswith("7.6.")
    assert closed["packaging"] == "24.2"
    assert closed["typing-extensions"] == "4.12.2"


def a_project(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "pyproject.toml"
    path.write_text(body)
    return path


def test_an_unpinned_dependency_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The check has to have been seen to fire, not only to pass."""
    project = a_project(
        tmp_path,
        '[project]\nname = "x"\nversion = "1.0.0"\ndependencies = ["click>=8"]\n',
    )
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("")
    monkeypatch.setattr("ginstand.tools.check_pins.project_file", lambda: project)
    monkeypatch.setattr("ginstand.tools.check_pins.constraints_file", lambda: constraints)
    messages = [finding.message for finding in findings()]
    assert any("is not pinned to an exact version" in message for message in messages)


def test_a_pin_missing_from_the_closure_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = a_project(
        tmp_path,
        '[project]\nname = "x"\nversion = "1.0.0"\ndependencies = ["click==8.1.8"]\n',
    )
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("# nothing\n")
    monkeypatch.setattr("ginstand.tools.check_pins.project_file", lambda: project)
    monkeypatch.setattr("ginstand.tools.check_pins.constraints_file", lambda: constraints)
    assert any("pinned in the project and not here" in f.message for f in findings())


def test_a_closure_that_disagrees_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = a_project(
        tmp_path,
        '[project]\nname = "x"\nversion = "1.0.0"\ndependencies = ["click==8.1.8"]\n',
    )
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("click==8.0.0\n")
    monkeypatch.setattr("ginstand.tools.check_pins.project_file", lambda: project)
    monkeypatch.setattr("ginstand.tools.check_pins.constraints_file", lambda: constraints)
    assert any("8.1.8 in the project and 8.0.0 here" in f.message for f in findings())


def test_a_range_in_the_closure_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = a_project(tmp_path, '[project]\nname = "x"\nversion = "1.0.0"\n')
    constraints = tmp_path / "constraints.txt"
    constraints.write_text("click>=8\n")
    monkeypatch.setattr("ginstand.tools.check_pins.project_file", lambda: project)
    monkeypatch.setattr("ginstand.tools.check_pins.constraints_file", lambda: constraints)
    assert any("is not an exact pin" in f.message for f in findings())
