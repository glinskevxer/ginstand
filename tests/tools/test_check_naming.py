"""The naming check, and the suite passing it."""

from __future__ import annotations

from pathlib import Path

import pytest

from ginstand.tools.check_naming import (
    BANNED_MODULES,
    MINIMUM_WORDS,
    VAGUE,
    check_module_names,
    check_test_file,
    collected_by_pytest,
    findings,
    named_tests,
)


def test_every_name_in_the_suite_reads_as_a_claim() -> None:
    assert list(findings()) == []


def test_no_module_is_called_something_undecided() -> None:
    assert list(check_module_names()) == []


def test_the_test_functions_of_a_file_are_found(tmp_path: Path) -> None:
    path = tmp_path / "test_m.py"
    path.write_text(
        '"""Tests."""\n\n\ndef test_a_thing_happens_the_way_it_should():\n    pass\n\n\n'
        "def helper():\n    pass\n"
    )
    assert [name for name, _ in named_tests(path)] == ["test_a_thing_happens_the_way_it_should"]


def test_a_name_too_short_to_be_a_claim_is_found(tmp_path: Path) -> None:
    path = tmp_path / "test_m.py"
    path.write_text('"""Tests."""\n\n\ndef test_weights_add():\n    pass\n')
    found = list(check_test_file(path))
    assert len(found) == 1
    assert f"a sentence takes {MINIMUM_WORDS}" in found[0].message


def test_a_name_of_exactly_the_minimum_is_taken(tmp_path: Path) -> None:
    path = tmp_path / "test_m.py"
    path.write_text('"""Tests."""\n\n\ndef test_days_between_is_signed():\n    pass\n')
    assert list(check_test_file(path)) == []


@pytest.mark.parametrize("word", sorted(VAGUE))
def test_every_vague_word_is_found(tmp_path: Path, word: str) -> None:
    path = tmp_path / "test_m.py"
    path.write_text(f'"""Tests."""\n\n\ndef test_the_thing_is_{word}_here_now():\n    pass\n')
    assert any("means nothing" in f.message for f in check_test_file(path))


def test_a_colour_grade_word_is_not_vague() -> None:
    assert "good" not in VAGUE
    assert "middling" not in VAGUE


def test_a_file_with_no_tests_in_it_is_clean(tmp_path: Path) -> None:
    path = tmp_path / "test_m.py"
    path.write_text('"""Tests."""\n\nCONSTANT = 1\n')
    assert list(check_test_file(path)) == []


def test_nothing_in_the_package_would_be_collected_as_a_test() -> None:
    assert list(collected_by_pytest()) == []


def test_the_banned_module_names_are_the_undecided_ones() -> None:
    assert "utils" in BANNED_MODULES
    assert "helpers" in BANNED_MODULES
