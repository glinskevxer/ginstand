"""The test mapping check, and the suite passing it."""

from __future__ import annotations

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
