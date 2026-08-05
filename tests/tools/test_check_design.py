"""The design note names code that is still there."""

from __future__ import annotations

import pytest

import ginstand.ginning.shares as shares
from ginstand.tools.base import repo_root
from ginstand.tools.check_design import (
    DOCUMENT,
    _has,
    bare_names,
    findings,
    note,
    paths,
    resolves,
    sections,
)


def test_the_note_names_only_code_that_is_there() -> None:
    assert list(findings()) == []


def test_the_note_is_where_the_check_looks() -> None:
    assert (repo_root() / DOCUMENT).is_file()
    assert "Why this is shaped the way it is" in note()


def test_the_dotted_paths_are_picked_out_in_order() -> None:
    found = paths()
    assert "ginstand.ginning.shares" in found
    assert "ginstand.quality.calibration" in found
    assert list(found) == list(dict.fromkeys(found))


def test_a_module_path_resolves() -> None:
    assert resolves("ginstand.ginning.shares")


def test_a_name_inside_a_module_resolves() -> None:
    assert resolves("ginstand.settle.close.close")


def test_something_that_is_not_there_does_not_resolve() -> None:
    assert not resolves("ginstand.nowhere")
    assert not resolves("ginstand.ginning.shares.nothing_at_all")


def test_every_section_has_a_heading_and_its_text() -> None:
    found = list(sections())
    assert len(found) >= 8
    for heading, body in found:
        assert heading
        assert heading in body


def test_the_bare_names_leave_the_dotted_paths_out() -> None:
    body = "`split_bales` in `ginstand.ginning.shares` does it"
    assert bare_names(body) == ("split_bales",)


def test_a_method_on_a_class_counts_as_the_module_offering_it() -> None:
    assert _has(shares, "split_bales")
    assert _has(shares, "for_producer")
    assert not _has(shares, "nothing_at_all")


def test_every_rule_worth_writing_down_has_a_section() -> None:
    headings = [heading for heading, _ in sections()]
    for wanted in ("carry", "staple ladder", "yard queue", "lease split"):
        assert any(wanted in heading for heading in headings), wanted


def test_a_note_naming_a_module_that_is_gone_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The check has to have been seen to fire, not only to pass."""
    monkeypatch.setattr(
        "ginstand.tools.check_design.note",
        lambda: "# x\n\n## A rule, in `ginstand.nowhere`\n\nIt does something.\n",
    )
    assert any("is not there any more" in f.message for f in findings())


def test_a_note_naming_a_function_that_is_gone_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ginstand.tools.check_design.note",
        lambda: ("# x\n\n## A rule, in `ginstand.ginning.shares`\n\n`nothing_at_all` does it.\n"),
    )
    assert any("nothing_at_all is not in" in f.message for f in findings())


def test_a_section_naming_no_module_is_left_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ginstand.tools.check_design.note",
        lambda: "# x\n\n## Nothing in particular\n\nJust prose about `things`.\n",
    )
    assert list(findings()) == []
