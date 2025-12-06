"""Our reason for condemning a bale is kept apart from the office's."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.classing.standing import OffSchedule, loan_eligible, standing_of
from ginstand.grades.color import ColorGrade
from ginstand.grades.matter import Extraneous, ExtraneousKind, ExtraneousLevel
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
    }
    fields.update(changes)
    return Classing(**fields)  # type: ignore[arg-type]


def test_an_ordinary_bale_is_on_the_schedule() -> None:
    standing = standing_of(a_card())
    assert standing.on_schedule
    assert not standing.below_grade
    assert standing.reasons == ()
    assert standing.line == "254120700061  on schedule"


def test_colour_rank_eight_takes_the_bale_off_the_schedule() -> None:
    standing = standing_of(a_card(color=ColorGrade(81)))
    assert standing.reasons == (OffSchedule.COLOUR,)
    assert standing.below_grade
    assert not standing.arguable


def test_leaf_eight_takes_the_bale_off_the_schedule() -> None:
    assert standing_of(a_card(leaf=8)).reasons == (OffSchedule.LEAF,)


def test_both_card_reasons_are_listed_when_both_apply() -> None:
    standing = standing_of(a_card(color=ColorGrade(83), leaf=8))
    assert standing.reasons == (OffSchedule.COLOUR, OffSchedule.LEAF)
    assert len(standing.carded_reasons) == 2


def test_heavy_plastic_is_the_gins_own_rule() -> None:
    card = a_card(extraneous=(Extraneous(ExtraneousKind.PLASTIC, ExtraneousLevel.HEAVY),))
    standing = standing_of(card)
    assert standing.reasons == (OffSchedule.PLASTIC,)
    assert standing.gin_reasons == (OffSchedule.PLASTIC,)
    assert standing.carded_reasons == ()
    assert standing.arguable


def test_light_plastic_is_noted_and_still_priced() -> None:
    card = a_card(extraneous=(Extraneous(ExtraneousKind.PLASTIC, ExtraneousLevel.LIGHT),))
    assert card.carries_plastic
    assert standing_of(card).on_schedule


def test_other_extraneous_matter_does_not_condemn_a_bale() -> None:
    for kind in (ExtraneousKind.BARK, ExtraneousKind.GRASS, ExtraneousKind.SEED_COAT):
        card = a_card(extraneous=(Extraneous(kind, ExtraneousLevel.HEAVY),))
        assert standing_of(card).on_schedule


def test_a_bale_off_for_both_reasons_is_not_arguable() -> None:
    card = a_card(
        color=ColorGrade(81),
        extraneous=(Extraneous(ExtraneousKind.PLASTIC, ExtraneousLevel.HEAVY),),
    )
    standing = standing_of(card)
    assert standing.reasons == (OffSchedule.COLOUR, OffSchedule.PLASTIC)
    assert not standing.arguable


def test_the_line_names_every_reason() -> None:
    card = a_card(leaf=8, extraneous=(Extraneous(ExtraneousKind.PLASTIC, ExtraneousLevel.HEAVY),))
    assert standing_of(card).line == ("254120700061  off schedule: leaf below grade, heavy plastic")


@pytest.mark.parametrize("enrolled", [True, False])
def test_a_below_grade_bale_is_never_loan_eligible(enrolled: bool) -> None:
    assert not loan_eligible(a_card(leaf=8), enrolled)


def test_loan_eligibility_needs_the_paperwork_as_well_as_the_cotton() -> None:
    assert loan_eligible(a_card(), enrolled=True)
    assert not loan_eligible(a_card(), enrolled=False)
