"""The pin check, and the project passing it."""

from __future__ import annotations

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
