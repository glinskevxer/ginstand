"""A ladder covers its range with no gap and no overlap, and that is checked."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ginstand.errors import ScheduleError, ValidationError
from ginstand.loan.points import Band, Ladder


def band(low: str, high: str, points: str, label: str = "") -> Band:
    return Band(Decimal(low), Decimal(high), Decimal(points), label)


def test_a_band_is_half_open_at_the_top() -> None:
    rung = band("3.7", "4.3", "125")
    assert rung.holds(Decimal("3.7"))
    assert rung.holds(Decimal("4.2"))
    assert not rung.holds(Decimal("4.3"))
    assert not rung.holds(Decimal("3.6"))


def test_an_empty_band_is_refused() -> None:
    with pytest.raises(ValidationError, match="empty or the wrong way round"):
        band("4.0", "4.0", "0")
    with pytest.raises(ValidationError, match="empty or the wrong way round"):
        band("4.3", "3.7", "0")


def test_a_band_prints_its_label_when_it_has_one() -> None:
    assert band("3.7", "4.3", "125", "premium range").name == "premium range"
    assert band("3.7", "4.3", "125").name == "3.7 to 4.3"


def test_a_ladder_reads_the_points_at_a_value() -> None:
    ladder = Ladder("micronaire", [band("3.0", "3.7", "-110"), band("3.7", "4.3", "125")])
    assert ladder.points_for(Decimal("3.5")) == Decimal("-110")
    assert ladder.points_for(Decimal("3.7")) == Decimal("125")


def test_a_ladder_sorts_the_bands_it_was_given() -> None:
    ladder = Ladder("micronaire", [band("3.7", "4.3", "125"), band("3.0", "3.7", "-110")])
    assert [rung.low for rung in ladder.bands] == [Decimal("3.0"), Decimal("3.7")]
    assert ladder.low == Decimal("3.0")
    assert ladder.high == Decimal("4.3")
    assert len(ladder) == 2


def test_a_gap_in_a_ladder_is_refused_when_it_is_built() -> None:
    with pytest.raises(ValidationError, match="has a gap between 3.7 and 3.9"):
        Ladder("micronaire", [band("3.0", "3.7", "-110"), band("3.9", "4.3", "125")])


def test_an_overlap_in_a_ladder_is_refused_when_it_is_built() -> None:
    with pytest.raises(ValidationError, match="overlaps between 3.5 and 3.7"):
        Ladder("micronaire", [band("3.0", "3.7", "-110"), band("3.5", "4.3", "125")])


def test_a_ladder_with_no_bands_is_refused() -> None:
    with pytest.raises(ValidationError, match="has no bands in it"):
        Ladder("micronaire", [])


def test_a_reading_the_ladder_does_not_cover_names_the_range() -> None:
    ladder = Ladder("micronaire", [band("3.0", "3.7", "-110")])
    with pytest.raises(ScheduleError, match="runs 3.0 to 3.7 and does not cover 4.4"):
        ladder.points_for(Decimal("4.4"))


def test_the_top_of_the_last_band_is_outside_the_ladder() -> None:
    ladder = Ladder("micronaire", [band("3.0", "3.7", "-110")])
    with pytest.raises(ScheduleError):
        ladder.points_for(Decimal("3.7"))


def test_the_band_itself_can_be_asked_for_so_a_statement_can_name_it() -> None:
    ladder = Ladder("micronaire", [band("3.7", "4.3", "125", "premium range")])
    assert ladder.band_for(Decimal("4.0")).name == "premium range"


def test_a_one_band_ladder_is_a_ladder() -> None:
    ladder = Ladder("strength", [band("15.0", "45.0", "0")])
    assert len(ladder) == 1
    assert ladder.points_for(Decimal("30.0")) == Decimal("0")
