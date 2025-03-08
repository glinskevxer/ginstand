"""The classing card is exactly what the office sent, and it grades only what it graded."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.classing.color import ColorGrade
from ginstand.classing.matter import Extraneous, ExtraneousKind, ExtraneousLevel
from ginstand.errors import ValidationError
from ginstand.model.classing import Classing


def a_card(**changes: object) -> Classing:
    fields: dict[str, object] = {
        "tag": "254120700061",
        "classed": date(2025, 10, 22),
        "color": ColorGrade(31),
        "leaf": 3,
        "staple": 35,
        "micronaire": Decimal("4.3"),
        "strength": Decimal("29.4"),
        "uniformity": Decimal("81.2"),
        "trash_pct": Decimal("0.6"),
    }
    fields.update(changes)
    return Classing(**fields)  # type: ignore[arg-type]


def test_a_card_normalises_the_tag_and_the_office() -> None:
    card = a_card(tag="25-41207-00061", office=" mem ")
    assert card.tag == "254120700061"
    assert card.office == "MEM"


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("micronaire", Decimal("1.9")),
        ("micronaire", Decimal("7.1")),
        ("strength", Decimal("14.9")),
        ("strength", Decimal("45.1")),
        ("uniformity", Decimal("64.9")),
        ("uniformity", Decimal("95.1")),
        ("trash_pct", Decimal("10.1")),
        ("trash_pct", Decimal("-0.1")),
    ],
)
def test_a_reading_outside_the_instrument_range_is_refused(name: str, value: Decimal) -> None:
    with pytest.raises(ValidationError, match="must be between"):
        a_card(**{name: value})


def test_readings_are_quantised_to_the_one_place_the_card_carries() -> None:
    card = a_card(micronaire=Decimal("4.34"), strength=Decimal("29.449"))
    assert card.micronaire == Decimal("4.3")
    assert card.strength == Decimal("29.4")


def test_a_bad_staple_or_leaf_is_caught_at_construction() -> None:
    with pytest.raises(ValidationError, match="staple"):
        a_card(staple=50)
    with pytest.raises(ValidationError, match="leaf grade"):
        a_card(leaf=9)


def test_the_card_reads_below_grade_off_colour_or_leaf() -> None:
    assert not a_card().below_grade_on_card
    assert a_card(color=ColorGrade(81)).below_grade_on_card
    assert a_card(leaf=8).below_grade_on_card


def test_plastic_does_not_make_the_card_say_below_grade() -> None:
    card = a_card(extraneous=(Extraneous(ExtraneousKind.PLASTIC, ExtraneousLevel.HEAVY),))
    assert card.carries_plastic
    assert not card.below_grade_on_card


def test_extraneous_notes_are_deduplicated_and_sorted() -> None:
    card = a_card(
        extraneous=(
            Extraneous(ExtraneousKind.PLASTIC),
            Extraneous(ExtraneousKind.BARK),
            Extraneous(ExtraneousKind.BARK),
        )
    )
    assert card.codes == "BK1 PL1"
    assert len(card.extraneous) == 2


def test_a_card_with_no_notes_prints_nothing_for_them() -> None:
    assert a_card().codes == ""
    assert not a_card().carries_plastic


def test_the_summary_line_carries_grade_leaf_staple_and_mic() -> None:
    assert a_card().summary == "31-3 35 mic 4.3"


def test_the_summary_appends_the_notes_when_there_are_any() -> None:
    card = a_card(extraneous=(Extraneous(ExtraneousKind.BARK, ExtraneousLevel.HEAVY),))
    assert card.summary == "31-3 35 mic 4.3 BK2"


def test_a_card_is_frozen() -> None:
    card = a_card()
    with pytest.raises(AttributeError):
        card.leaf = 1  # type: ignore[misc]
