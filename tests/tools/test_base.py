"""What every check shares: finding the source and reporting findings."""

from __future__ import annotations

from pathlib import Path

import pytest

from ginstand.tools.base import (
    Finding,
    module_name,
    repo_root,
    report,
    source_files,
    source_root,
    suite_files,
)


def test_the_source_root_is_the_package_directory() -> None:
    assert source_root().name == "ginstand"
    assert (source_root() / "errors.py").is_file()


def test_the_repo_root_holds_the_source_directory() -> None:
    assert (repo_root() / "src" / "ginstand").is_dir()


def test_every_source_file_is_found_in_path_order() -> None:
    paths = list(source_files())
    assert paths == sorted(paths)
    assert any(path.name == "errors.py" for path in paths)
    assert all(path.suffix == ".py" for path in paths)


def test_a_directory_can_be_skipped() -> None:
    without = list(source_files(skip=("tools",)))
    assert not any("tools" in path.parts for path in without)
    assert len(without) < len(list(source_files()))


def test_the_suite_files_are_found() -> None:
    names = {path.name for path in suite_files()}
    assert "test_base.py" in names


def test_a_module_name_is_dotted_and_drops_the_init() -> None:
    assert module_name(source_root() / "errors.py") == "ginstand.errors"
    assert module_name(source_root() / "units" / "weight.py") == "ginstand.units.weight"
    assert module_name(source_root() / "units" / "__init__.py") == "ginstand.units"


def test_a_finding_prints_relative_to_the_checkout() -> None:
    finding = Finding(source_root() / "errors.py", 12, "something")
    assert str(finding) == "src/ginstand/errors.py:12: something"


def test_reporting_nothing_is_clean(capsys: pytest.CaptureFixture[str]) -> None:
    assert report("a check", []) == 0
    assert "a check: clean" in capsys.readouterr().out


def test_reporting_findings_fails_and_counts_them(
    capsys: pytest.CaptureFixture[str],
) -> None:
    findings = [
        Finding(Path("a.py"), 1, "one"),
        Finding(Path("b.py"), 2, "two"),
    ]
    assert report("a check", findings) == 1
    output = capsys.readouterr().out
    assert "one" in output
    assert "a check: 2 problems" in output
