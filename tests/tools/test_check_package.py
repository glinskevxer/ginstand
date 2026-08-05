"""The package shape check, and the package passing it."""

from __future__ import annotations

from pathlib import Path

import pytest

from ginstand.tools.base import repo_root, source_root
from ginstand.tools.check_package import findings, package_directories, project


def test_the_package_is_shaped_to_ship() -> None:
    assert list(findings()) == []


def test_every_directory_in_the_package_is_a_package() -> None:
    for directory in package_directories():
        assert (directory / "__init__.py").is_file(), directory


def test_the_subpackages_are_the_ones_the_readme_lists() -> None:
    names = {directory.name for directory in package_directories()}
    assert names == {
        "units",
        "grades",
        "model",
        "store",
        "yard",
        "ginning",
        "classing",
        "loan",
        "charges",
        "warehouse",
        "quality",
        "settle",
        "report",
        "cli",
        "tools",
    }


def test_every_test_directory_is_a_package() -> None:
    tests = repo_root() / "tests"
    for directory in sorted(tests.rglob("*")):
        if directory.is_dir() and not directory.name.startswith((".", "_")):
            assert (directory / "__init__.py").is_file(), directory


def test_the_wheel_packages_the_source_directory() -> None:
    data = project()
    wheel = data["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert wheel["packages"] == ["src/ginstand"]


def test_the_console_script_names_a_real_function() -> None:
    scripts = project()["project"]["scripts"]
    assert scripts["ginstand"] == "ginstand.cli.main:run"


def test_no_module_at_the_root_shadows_the_standard_library() -> None:
    import sys

    for path in source_root().glob("*.py"):
        assert path.stem not in sys.stdlib_module_names, path


def test_a_directory_with_no_init_file_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The check has to have been seen to fire, not only to pass."""
    root = tmp_path / "ginstand"
    (root / "orphan").mkdir(parents=True)
    (root / "__init__.py").write_text('"""x."""\n')
    monkeypatch.setattr("ginstand.tools.check_package.source_root", lambda: root)
    messages = [finding.message for finding in findings()]
    assert any("no __init__.py, so it will not ship" in message for message in messages)


def test_a_test_directory_with_no_init_file_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "tests" / "orphan").mkdir(parents=True)
    monkeypatch.setattr("ginstand.tools.check_package.repo_root", lambda: tmp_path)
    assert any("test directory with no __init__.py" in f.message for f in findings())


def test_a_module_that_shadows_the_standard_library_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "ginstand"
    root.mkdir(parents=True)
    (root / "__init__.py").write_text('"""x."""\n')
    (root / "json.py").write_text('"""x."""\n')
    monkeypatch.setattr("ginstand.tools.check_package.source_root", lambda: root)
    assert any("standard library module" in f.message for f in findings())
