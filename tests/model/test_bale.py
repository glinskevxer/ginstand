"""A bale carries its tag, its weights and the moisture it was pressed at."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import ValidationError
from ginstand.ids import Pbi
from ginstand.model.bale import MAX_BALE_POUNDS, MIN_BALE_POUNDS, Bale


def a_bale(**changes: object) -> Bale:
    fields: dict[str, object] = {
        "tag": "254120700061",
        "run": "gr-2025-04",
        "pressed": date(2025, 10, 14),
        "gross_pounds": 512,
        "tare_pounds": 22,
        "moisture_pct": Decimal("6.8"),
    }
    fields.update(changes)
    return Bale(**fields)  # type: ignore[arg-type]


def test_a_bale_keeps_its_tag_as_twelve_digits_however_it_was_typed() -> None:
    assert a_bale(tag="25-41207-00061").tag == "254120700061"
    assert a_bale(tag=" 25 41207 00061 ").tag == "254120700061"


def test_a_bad_tag_is_caught_at_construction() -> None:
    with pytest.raises(ValidationError, match="must be 12 digits"):
        a_bale(tag="2541207")


def test_net_weight_is_gross_less_the_bagging_and_ties() -> None:
    assert a_bale().net_pounds == 490


def test_the_tag_reads_back_as_its_parts() -> None:
    assert a_bale().pbi == Pbi(crop_year=2025, gin_code="41207", sequence=61)
    assert a_bale().crop_year == 2025
    assert a_bale().sequence == 61


def test_a_press_cycle_that_made_no_saleable_bale_is_refused() -> None:
    with pytest.raises(ValidationError, match=f"at least {MIN_BALE_POUNDS} lb for a bale"):
        a_bale(gross_pounds=300, tare_pounds=22)


def test_two_cycles_weighed_together_are_refused() -> None:
    with pytest.raises(ValidationError, match=f"no more than {MAX_BALE_POUNDS} lb"):
        a_bale(gross_pounds=800, tare_pounds=22)


@pytest.mark.parametrize("tare", [0, 3, 41, 100])
def test_a_tare_outside_the_bagging_and_ties_range_is_refused(tare: int) -> None:
    with pytest.raises(ValidationError, match="bagging and ties weigh"):
        a_bale(tare_pounds=tare)


def test_the_tare_is_kept_on_the_bale_not_applied_as_a_constant() -> None:
    assert a_bale(tare_pounds=22).net_pounds == 490
    assert a_bale(tare_pounds=26).net_pounds == 486


def test_dry_weight_comes_off_the_press_moisture() -> None:
    assert a_bale(moisture_pct=Decimal("6.8")).dry_pounds == 457


def test_a_bale_at_or_under_the_storage_ceiling_can_go_to_the_warehouse() -> None:
    assert a_bale(moisture_pct=Decimal("7.5")).storable
    assert not a_bale(moisture_pct=Decimal("7.6")).storable


def test_a_bale_is_frozen() -> None:
    bale = a_bale()
    with pytest.raises(AttributeError):
        bale.gross_pounds = 600  # type: ignore[misc]


def test_the_gin_stand_is_optional_and_stripped() -> None:
    assert a_bale().stand == ""
    assert a_bale(stand=" 3 ").stand == "3"
