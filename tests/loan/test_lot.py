"""A lot's rate is weighted, and refused bales are named rather than dropped."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.classing.color import ColorGrade
from ginstand.errors import ValidationError
from ginstand.loan.lot import value_lot
from ginstand.loan.schedule import schedule_for
from ginstand.model.classing import Classing
from ginstand.units.money import format_money

SCHEDULE = schedule_for(2025)


def a_card(sequence: int = 61, **changes: object) -> Classing:
    fields: dict[str, object] = {
        "tag": f"2541207{sequence:05d}",
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


def test_a_lot_adds_the_bale_values() -> None:
    lot = value_lot(SCHEDULE, [(a_card(1), 490), (a_card(2), 500)])
    assert lot.bales == 2
    assert lot.net_pounds == 990
    assert format_money(lot.value) == "$514.80"


def test_the_average_rate_is_weighted_by_weight() -> None:
    heavy = a_card(1, color=ColorGrade(11))
    light = a_card(2, color=ColorGrade(51))
    lot = value_lot(SCHEDULE, [(heavy, 700), (light, 300)])
    unweighted = (Decimal("53.3000") + Decimal("49.4000")) / 2
    assert lot.average_rate != unweighted
    assert lot.average_rate == Decimal("52.1300")


def test_a_lot_of_one_rate_averages_to_that_rate() -> None:
    lot = value_lot(SCHEDULE, [(a_card(1), 490), (a_card(2), 510)])
    assert lot.average_rate == Decimal("52.0000")


def test_refused_bales_are_counted_and_named() -> None:
    lot = value_lot(SCHEDULE, [(a_card(1), 490), (a_card(2, leaf=8), 500)])
    assert lot.bales == 2
    assert len(lot.taken) == 1
    assert len(lot.refused) == 1
    assert lot.refusals == {"leaf below grade": 1}


def test_refused_bales_keep_their_weight_in_the_lot_total() -> None:
    lot = value_lot(SCHEDULE, [(a_card(1), 490), (a_card(2, leaf=8), 500)])
    assert lot.net_pounds == 990
    assert lot.taken_pounds == 490


def test_the_rate_is_worked_out_over_the_bales_taken_only() -> None:
    lot = value_lot(SCHEDULE, [(a_card(1), 490), (a_card(2, leaf=8), 500)])
    assert lot.average_rate == Decimal("52.0000")


def test_several_reasons_are_counted_apart() -> None:
    lot = value_lot(
        SCHEDULE,
        [
            (a_card(1), 490),
            (a_card(2, leaf=8), 500),
            (a_card(3, color=ColorGrade(81)), 480),
            (a_card(4, leaf=8), 495),
        ],
    )
    assert lot.refusals == {"leaf below grade": 2, "colour below grade": 1}


def test_a_lot_the_loan_takes_nothing_from_has_no_rate() -> None:
    lot = value_lot(SCHEDULE, [(a_card(1, leaf=8), 490)])
    assert lot.taken == ()
    assert lot.value == 0
    with pytest.raises(ValidationError, match="has no bales the loan will take"):
        assert lot.average_rate


def test_an_unenrolled_producer_has_every_bale_refused() -> None:
    lot = value_lot(SCHEDULE, [(a_card(1), 490), (a_card(2), 500)], enrolled=False)
    assert len(lot.refused) == 2
    assert lot.refusals == {"the producer is not enrolled for the loan": 2}


def test_an_empty_lot_is_refused() -> None:
    with pytest.raises(ValidationError, match="has no bales in it"):
        value_lot(SCHEDULE, [])


def test_the_lot_line_says_how_many_were_refused() -> None:
    plain = value_lot(SCHEDULE, [(a_card(1), 490)])
    assert plain.line == "1 bales  490 lb  $254.80"
    mixed = value_lot(SCHEDULE, [(a_card(1), 490), (a_card(2, leaf=8), 500)])
    assert mixed.line.startswith("2 bales, 1 refused  990 lb")
