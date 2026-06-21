"""The glossary, and the one on disk being current."""

from __future__ import annotations

from pathlib import Path

import pytest

from ginstand.tools.base import repo_root, source_root
from ginstand.tools.build_glossary import DOCUMENT, build, constants, main, terms, words


def test_the_glossary_on_disk_is_current() -> None:
    assert (repo_root() / DOCUMENT).read_text() == build()


def test_the_glossary_check_passes_as_it_stands(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.argv", ["build_glossary", "--check"])
    main()
    assert "build_glossary: clean" in capsys.readouterr().out


def test_the_numbers_the_office_argues_about_are_in_it() -> None:
    text = build()
    for name in (
        "SAFE_BALE_MOISTURE",
        "RISK_LIMIT",
        "MAX_ADDED_FRACTION",
        "SAMPLE_HELD_DAYS",
        "LOW_TURNOUT",
    ):
        assert f"**{name}**" in text


def test_a_constant_carries_its_value() -> None:
    assert "**SAMPLE_HELD_DAYS** = `28`" in build()


def test_the_enum_members_are_explained() -> None:
    text = build()
    assert "**HoldReason.PLASTIC**" in text
    assert "**EntryKind.PAYMENT**" in text
    assert "**ColorGroup.WHITE**" not in text


def test_an_undocumented_constant_is_left_out(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text('"""A module."""\n\nQUIET = 1\n\nLOUD = 2\n"""Says something."""\n')
    found = list(constants(path))
    assert [term.name for term in found] == ["LOUD"]


def test_a_lower_case_name_is_not_a_constant(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text('"""A module."""\n\nthing = 1\n"""Says something."""\n')
    assert list(constants(path)) == []


def test_an_enum_member_with_no_docstring_is_left_out(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text(
        '"""A module."""\n\nfrom enum import StrEnum\n\n\nclass Kind(StrEnum):\n'
        '    """A kind."""\n\n    QUIET = "quiet"\n\n    LOUD = "loud"\n'
        '    """Says something."""\n'
    )
    assert [term.name for term in words(path)] == ["Kind.LOUD"]


def test_a_class_that_is_not_an_enum_is_left_out(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text(
        '"""A module."""\n\n\nclass Thing:\n    """A thing."""\n\n    LOUD = 2\n'
        '    """Says something."""\n'
    )
    assert list(words(path)) == []


def test_the_checks_are_left_out_of_the_glossary() -> None:
    assert not any(term.module.startswith("ginstand.tools") for term in terms())
    assert (source_root() / "tools" / "base.py").is_file()


def test_the_terms_are_in_module_then_name_order() -> None:
    keys = [(term.module, term.name) for term in terms()]
    assert keys == sorted(keys)
