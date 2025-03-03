"""Leaf is graded, extraneous matter is noted, and plastic is the one that matters."""

from __future__ import annotations

import pytest

from ginstand.classing.matter import (
    BELOW_GRADE_LEAF,
    Extraneous,
    ExtraneousKind,
    ExtraneousLevel,
    carries_plastic,
    leaf_below_grade,
    leaf_grade,
    parse_extraneous,
)
from ginstand.errors import ValidationError


@pytest.mark.parametrize("grade", [1, 2, 3, 4, 5, 6, 7, 8])
def test_every_leaf_grade_on_the_card_passes(grade: int) -> None:
    assert leaf_grade(grade) == grade


@pytest.mark.parametrize("grade", [0, 9, -1, 80])
def test_a_leaf_grade_off_the_card_is_refused(grade: int) -> None:
    with pytest.raises(ValidationError, match="between 1 and 8"):
        leaf_grade(grade)


def test_a_bool_is_not_a_leaf_grade() -> None:
    with pytest.raises(ValidationError, match="whole number from 1 to 8"):
        leaf_grade(True)


def test_only_leaf_eight_is_below_grade() -> None:
    assert leaf_below_grade(BELOW_GRADE_LEAF)
    assert not leaf_below_grade(7)
    assert not leaf_below_grade(1)


def test_an_extraneous_note_prints_as_its_code_and_level() -> None:
    note = Extraneous(kind=ExtraneousKind.BARK, level=ExtraneousLevel.HEAVY)
    assert note.code == "BK2"
    assert str(note) == "BK2"
    assert note.heavy


def test_a_note_defaults_to_light() -> None:
    note = Extraneous(kind=ExtraneousKind.GRASS)
    assert note.level is ExtraneousLevel.LIGHT
    assert note.code == "GR1"
    assert not note.heavy


@pytest.mark.parametrize(
    ("written", "kind", "level"),
    [
        ("BK1", ExtraneousKind.BARK, ExtraneousLevel.LIGHT),
        ("pl2", ExtraneousKind.PLASTIC, ExtraneousLevel.HEAVY),
        (" sc1 ", ExtraneousKind.SEED_COAT, ExtraneousLevel.LIGHT),
        ("OT2", ExtraneousKind.OTHER, ExtraneousLevel.HEAVY),
    ],
)
def test_a_note_reads_off_a_card(
    written: str, kind: ExtraneousKind, level: ExtraneousLevel
) -> None:
    assert parse_extraneous(written) == Extraneous(kind=kind, level=level)


@pytest.mark.parametrize("written", ["", "BK", "BK12", "ZZ1", "BK3", "BK0"])
def test_a_note_that_is_not_on_the_code_list_is_refused(written: str) -> None:
    with pytest.raises(ValidationError):
        parse_extraneous(written)


def test_every_kind_has_a_code_that_reads_back() -> None:
    for kind in ExtraneousKind:
        note = Extraneous(kind=kind, level=ExtraneousLevel.LIGHT)
        assert parse_extraneous(note.code) == note


def test_plastic_is_found_at_either_level() -> None:
    light = Extraneous(kind=ExtraneousKind.PLASTIC, level=ExtraneousLevel.LIGHT)
    heavy = Extraneous(kind=ExtraneousKind.PLASTIC, level=ExtraneousLevel.HEAVY)
    bark = Extraneous(kind=ExtraneousKind.BARK)
    assert carries_plastic((light,))
    assert carries_plastic((bark, heavy))
    assert not carries_plastic((bark,))
    assert not carries_plastic(())


def test_notes_sort_so_a_card_prints_them_the_same_way_twice() -> None:
    notes = (
        Extraneous(kind=ExtraneousKind.PLASTIC),
        Extraneous(kind=ExtraneousKind.BARK, level=ExtraneousLevel.HEAVY),
        Extraneous(kind=ExtraneousKind.BARK),
    )
    assert [note.code for note in sorted(notes)] == ["BK1", "BK2", "PL1"]
