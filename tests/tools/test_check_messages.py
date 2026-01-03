"""The message check, and the package passing it."""

from __future__ import annotations

from pathlib import Path

import pytest

from ginstand.tools.check_messages import MACHINE_WORDS, RAISED, check_file, findings

HEADER = '"""A module."""\n\nfrom ginstand.errors import StateError, ValidationError\n\n\n'


def a_module(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "m.py"
    path.write_text(f'{HEADER}def work():\n    """Work."""\n    {body}\n')
    return path


def test_every_message_in_the_package_reads_the_same_way() -> None:
    assert list(findings()) == []


def test_a_message_that_starts_upper_case_is_found(tmp_path: Path) -> None:
    path = a_module(tmp_path, 'raise StateError("Gin run GR-1 is closed")')
    assert [f.message for f in check_file(path)] == [
        "the message starts upper case: 'Gin run GR-1 is closed'"
    ]


def test_a_message_that_ends_in_a_full_stop_is_found(tmp_path: Path) -> None:
    path = a_module(tmp_path, 'raise StateError("gin run GR-1 is closed.")')
    found = list(check_file(path))
    assert len(found) == 1
    assert "ends in a full stop" in found[0].message


@pytest.mark.parametrize("word", MACHINE_WORDS)
def test_a_message_that_names_the_machinery_is_found(tmp_path: Path, word: str) -> None:
    path = a_module(tmp_path, f'raise StateError("the {word} was wrong")')
    assert any("which is machinery" in f.message for f in check_file(path))


def test_a_plain_message_is_clean(tmp_path: Path) -> None:
    path = a_module(tmp_path, 'raise StateError("gin run GR-1 is closed")')
    assert list(check_file(path)) == []


def test_the_field_argument_of_a_validation_error_is_not_the_message(
    tmp_path: Path,
) -> None:
    path = a_module(tmp_path, 'raise ValidationError("Rd", "must be a number")')
    assert list(check_file(path)) == []


def test_the_message_of_a_validation_error_is_checked(tmp_path: Path) -> None:
    path = a_module(tmp_path, 'raise ValidationError("rd", "Must be a number")')
    assert len(list(check_file(path))) == 1


def test_a_message_built_only_from_values_is_left_alone(tmp_path: Path) -> None:
    path = a_module(tmp_path, 'raise StateError(f"{1} is closed")')
    assert list(check_file(path)) == []


def test_an_f_string_that_starts_with_words_is_checked(tmp_path: Path) -> None:
    path = a_module(tmp_path, 'raise StateError(f"Gin run {1} is closed")')
    assert len(list(check_file(path))) == 1


def test_the_types_that_build_their_own_message_are_skipped() -> None:
    assert RAISED["NotFoundError"] is None
    assert RAISED["DuplicateError"] is None
    assert RAISED["ValidationError"] == 1
