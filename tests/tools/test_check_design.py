"""The design note names code that is still there."""

from __future__ import annotations

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
