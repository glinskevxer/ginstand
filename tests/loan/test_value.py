"""A bale's value is one multiplication and five tables, and the working is kept."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.classing.color import ColorGrade
from ginstand.classing.matter import Extraneous, ExtraneousKind, ExtraneousLevel
from ginstand.loan.schedule import Schedule, schedule_for
from ginstand.loan.value import MINIMUM_RATE, value_bale
from ginstand.model.classing import Classing
from ginstand.units.money import format_money

SCHEDULE = schedule_for(2025)


def a_card(**changes: object) -> Classing:
    fields: dict[str, object] = {
        "tag": "254120700061",
        "classed": date(2025, 10, 22),
        "color": ColorGrade(31),
        "leaf": 3,
        "staple": 34,
        "micronaire": Decimal("4.5"),
        "strength": Decimal("27.0"),
        "uniformity": Decimal("81.0"),
    }
    fields.update(changes)
    return Classing(**fields)  # type: ignore[arg-type]


def test_a_base_bale_is_worth_the_base_rate() -> None:
    valuation = value_bale(SCHEDULE, a_card(), 490)
    assert valuation.total_points == Decimal("0")
    assert valuation.rate == Decimal("52.0000")
    assert format_money(valuation.value) == "$254.80"


def test_every_table_puts_a_line_on_the_valuation() -> None:
    valuation = value_bale(SCHEDULE, a_card(), 490)
    assert [line.name for line in valuation.lines] == [
        "colour",
        "leaf",
        "staple",
        "micronaire",
        "strength",
        "uniformity",
    ]


def test_the_lines_add_up_to_the_rate() -> None:
    valuation = value_bale(
        SCHEDULE,
        a_card(color=ColorGrade(21), leaf=2, staple=36, micronaire=Decimal("4.0")),
        490,
    )
    assert valuation.total_points == Decimal("75") + Decimal("10") + Decimal("245") + Decimal("125")
    assert valuation.rate == Decimal("52.0000") + Decimal("455") / 100


def test_a_better_bale_is_worth_more() -> None:
    plain = value_bale(SCHEDULE, a_card(), 490).value
    better = value_bale(SCHEDULE, a_card(color=ColorGrade(11), staple=38), 490).value
    assert better > plain


def test_the_same_staple_is_worth_less_once_the_colour_drops_a_group() -> None:
    white = value_bale(SCHEDULE, a_card(color=ColorGrade(32), staple=37), 490)
    spotted = value_bale(SCHEDULE, a_card(color=ColorGrade(33), staple=37), 490)
    colour_gap = SCHEDULE.colour_points(ColorGrade(32)) - SCHEDULE.colour_points(ColorGrade(33))
    assert white.total_points - spotted.total_points > colour_gap


def test_a_below_grade_bale_has_no_loan_value_and_says_why() -> None:
    valuation = value_bale(SCHEDULE, a_card(leaf=8), 490)
    assert not valuation.eligible
    assert valuation.rate == MINIMUM_RATE
    assert valuation.value == 0
    assert valuation.refusal == "leaf below grade"
    assert valuation.lines == ()


def test_heavy_plastic_takes_the_value_off_a_bale_the_office_priced() -> None:
    card = a_card(extraneous=(Extraneous(ExtraneousKind.PLASTIC, ExtraneousLevel.HEAVY),))
    valuation = value_bale(SCHEDULE, card, 490)
    assert not valuation.eligible
    assert valuation.refusal == "heavy plastic"


def test_a_producer_who_is_not_enrolled_has_no_loan_value() -> None:
    valuation = value_bale(SCHEDULE, a_card(), 490, enrolled=False)
    assert not valuation.eligible
    assert valuation.value == 0
    assert valuation.refusal == "the producer is not enrolled for the loan"


def test_the_cotton_reason_is_given_before_the_paperwork_one() -> None:
    valuation = value_bale(SCHEDULE, a_card(leaf=8), 490, enrolled=False)
    assert valuation.refusal == "leaf below grade"


def test_the_worst_bale_the_tables_can_price_is_still_worth_something() -> None:
    card = a_card(
        color=ColorGrade(54),
        leaf=7,
        staple=24,
        micronaire=Decimal("2.1"),
        strength=Decimal("16.0"),
        uniformity=Decimal("70.0"),
    )
    valuation = value_bale(SCHEDULE, card, 490)
    assert valuation.total_points == Decimal("-2585")
    assert valuation.rate == Decimal("26.1500")
    assert valuation.value > 0


def test_the_rate_is_floored_at_zero_if_a_year_publishes_a_low_base() -> None:
    lean = Schedule(crop_year=2025, base_rate=Decimal("20.0000"))
    card = a_card(
        color=ColorGrade(54),
        leaf=7,
        staple=24,
        micronaire=Decimal("2.1"),
        strength=Decimal("16.0"),
        uniformity=Decimal("70.0"),
    )
    valuation = value_bale(lean, card, 490)
    assert valuation.base_rate + valuation.total_points / 100 < 0
    assert valuation.rate == MINIMUM_RATE
    assert valuation.value == 0


def test_the_summary_reads_as_a_bale_list_line() -> None:
    valuation = value_bale(SCHEDULE, a_card(), 490)
    assert valuation.summary == "254120700061  490 lb at 52.00c  $254.80"


def test_the_summary_of_a_refused_bale_names_the_reason() -> None:
    assert value_bale(SCHEDULE, a_card(leaf=8), 490).summary == (
        "254120700061  no loan value: leaf below grade"
    )


def test_the_working_starts_at_the_base_and_ends_at_the_rate() -> None:
    working = value_bale(SCHEDULE, a_card(), 490).working
    assert working[0].startswith("base")
    assert working[-1].startswith("rate")
    assert len(working) == 8


def test_a_premium_line_carries_its_sign() -> None:
    valuation = value_bale(SCHEDULE, a_card(micronaire=Decimal("4.0")), 490)
    mic = next(line for line in valuation.lines if line.name == "micronaire")
    assert mic.text.endswith("+125")


@pytest.mark.parametrize("pounds", [0, 300, 490, 750])
def test_the_value_scales_with_the_weight(pounds: int) -> None:
    valuation = value_bale(SCHEDULE, a_card(), pounds)
    assert valuation.value == round(pounds * 52)
