"""The test mapping check, and the suite passing it."""

from __future__ import annotations

from pathlib import Path

import pytest

from ginstand.tools.base import repo_root, source_root
from ginstand.tools.check_tests import expected_test, findings, orphans


def test_every_module_has_a_test_module() -> None:
    assert list(findings()) == []


def test_no_test_module_is_left_behind() -> None:
    assert list(orphans()) == []


def test_the_mapping_mirrors_the_source_tree() -> None:
    assert expected_test(source_root() / "units" / "weight.py") == (
        repo_root() / "tests" / "units" / "test_weight.py"
    )
    assert expected_test(source_root() / "errors.py") == (repo_root() / "tests" / "test_errors.py")


def test_the_check_finds_a_module_with_no_test() -> None:
    wanted = expected_test(source_root() / "units" / "nothing.py")
    assert not wanted.is_file()
    assert wanted.name == "test_nothing.py"


def test_a_module_with_no_test_module_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The check has to have been seen to fire, not only to pass."""
    root = tmp_path / "src" / "ginstand"
    root.mkdir(parents=True)
    orphan = root / "orphan.py"
    orphan.write_text('"""x."""\n')
    monkeypatch.setattr("ginstand.tools.check_tests.source_root", lambda: root)
    monkeypatch.setattr("ginstand.tools.check_tests.repo_root", lambda: tmp_path)
    monkeypatch.setattr("ginstand.tools.check_tests.source_files", lambda: [orphan])
    messages = [finding.message for finding in findings()]
    assert any("has no test module at" in message for message in messages)


def test_a_test_module_with_no_source_module_is_reported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "src" / "ginstand").mkdir(parents=True)
    (tmp_path / "tests").mkdir(parents=True)
    (tmp_path / "tests" / "test_gone.py").write_text('"""x."""\n')
    monkeypatch.setattr(
        "ginstand.tools.check_tests.source_root", lambda: tmp_path / "src" / "ginstand"
    )
    monkeypatch.setattr("ginstand.tools.check_tests.repo_root", lambda: tmp_path)
    assert any("not there any more" in f.message for f in orphans())
