"""A run is measured on the target and a bale on its own run."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import StateError
from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.model.farm import Farm, Field
from ginstand.model.module import Module, ModuleKind, WrapKind
from ginstand.model.producer import Lease, LeaseKind, Producer
from ginstand.quality.tolerance import (
    BALE_TOLERANCE,
    MINIMUM_BALES,
    RUN_TOLERANCE,
    TARGET_POUNDS,
    control_for,
    mean_of,
    outliers_in,
    season_control,
)
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

OPENED = date(2025, 10, 14)


@pytest.fixture
def gin(book: Book) -> Book:
    book.producers.add(Producer(ref="P-12", name="Aldys Brothers"))
    book.leases.add(Lease(ref="L-1", tenant="P-12", kind=LeaseKind.OWNER))
    book.farms.add(Farm(ref="F-3", producer="P-12", name="Home Place"))
    book.fields.add(
        Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("78.4"), lease="L-1")
    )
    return book


def a_run(gin: Book, ref: str, weights: tuple[int, ...], day: date = OPENED) -> None:
    open_run(gin, ref, "41207", day)
    tag = f"M-{ref}"
    receive(
        gin,
        Module(
            tag=tag,
            field="FL-9",
            kind=ModuleKind.RECTANGULAR,
            harvested=date(2025, 9, 28),
            received=date(2025, 10, 2),
            gross_pounds=76_140,
            tare_pounds=26_140,
            moisture_pct=Decimal("9.4"),
            wrap=WrapKind.TARP,
        ),
    )
    feed(gin, ref, tag, day)
    for net in weights:
        press(gin, ref, day, net + 22, 22, Decimal("6.8"))
    close_run(gin, ref, day)


def test_a_run_with_no_bales_has_no_control(gin: Book) -> None:
    open_run(gin, "GR-1", "41207", OPENED)
    with pytest.raises(StateError, match="has pressed no bales"):
        control_for(gin, "GR-1")


def test_a_mean_needs_something_to_average() -> None:
    with pytest.raises(StateError, match="no bales to take a mean of"):
        mean_of(())


def test_a_run_on_target_is_in_control(gin: Book) -> None:
    a_run(gin, "GR-1", (500, 498, 502, 501, 499, 500))
    control = control_for(gin, "GR-1")
    assert control.mean == Decimal("500.0")
    assert control.off_target == Decimal("0.0")
    assert control.in_control
    assert control.clean


def test_a_run_making_light_bales_is_queried(gin: Book) -> None:
    a_run(gin, "GR-1", (460,) * 6)
    control = control_for(gin, "GR-1")
    assert control.off_target == Decimal("-40.0")
    assert abs(control.off_target) > RUN_TOLERANCE
    assert not control.in_control
    assert "PRESS" in control.line


def test_a_run_inside_the_tolerance_is_not_queried(gin: Book) -> None:
    a_run(gin, "GR-1", (TARGET_POUNDS - RUN_TOLERANCE,) * 6)
    assert control_for(gin, "GR-1").in_control


def test_a_bale_is_measured_against_its_own_run(gin: Book) -> None:
    a_run(gin, "GR-1", (440,) * 6)
    a_run(gin, "GR-2", (500,) * 20 + (440,), day=date(2025, 10, 20))
    assert control_for(gin, "GR-1").outliers == ()
    assert len(control_for(gin, "GR-2").outliers) == 1


def test_the_same_weight_is_a_finding_on_one_run_and_not_on_another(
    gin: Book,
) -> None:
    a_run(gin, "GR-1", (440,) * 6)
    a_run(gin, "GR-2", (500,) * 20 + (440,), day=date(2025, 10, 20))
    assert "254120700001" not in control_for(gin, "GR-1").outliers
    assert control_for(gin, "GR-2").outliers == ("254120700027",)


def test_the_two_judgements_are_separate(gin: Book) -> None:
    a_run(gin, "GR-1", (440,) * 6)
    control = control_for(gin, "GR-1")
    assert not control.in_control
    assert control.outliers == ()
    assert not control.clean


def test_a_short_run_is_measured_on_the_target(gin: Book) -> None:
    a_run(gin, "GR-1", (440, 440, 440))
    control = control_for(gin, "GR-1")
    assert control.bales < MINIMUM_BALES
    assert control.basis == Decimal(TARGET_POUNDS)
    assert len(control.outliers) == 3


def test_a_long_run_is_measured_on_its_own_mean(gin: Book) -> None:
    a_run(gin, "GR-1", (440,) * MINIMUM_BALES)
    control = control_for(gin, "GR-1")
    assert control.basis == control.mean
    assert control.outliers == ()


def test_the_spread_is_the_heaviest_less_the_lightest(gin: Book) -> None:
    a_run(gin, "GR-1", (480, 500, 520, 495, 505, 500))
    control = control_for(gin, "GR-1")
    assert control.lightest == 480
    assert control.heaviest == 520
    assert control.spread == 40


def test_the_outliers_are_listed_worst_first(gin: Book) -> None:
    a_run(gin, "GR-1", (500,) * 10 + (440, 400))
    found = outliers_in(gin, "GR-1")
    assert [item[1] for item in found] == [400, 440]
    assert abs(found[0][2]) > abs(found[1][2])


def test_the_bale_tolerance_is_inclusive(gin: Book) -> None:
    on_the_line = 500 - BALE_TOLERANCE
    a_run(gin, "GR-1", (500, 500, 500, 500, 500, 500))
    a_run(gin, "GR-2", (500, 500, 500, 500, 500, on_the_line), day=date(2025, 10, 20))
    control = control_for(gin, "GR-2")
    off = abs(Decimal(on_the_line) - control.basis)
    assert off < BALE_TOLERANCE
    assert control.outliers == ()


def test_the_season_lists_the_worst_run_first(gin: Book) -> None:
    a_run(gin, "GR-1", (500,) * 6)
    a_run(gin, "GR-2", (440,) * 6, day=date(2025, 10, 20))
    assert [item.run for item in season_control(gin, 2025)] == ["GR-2", "GR-1"]


def test_a_run_with_no_bales_is_left_off_the_season(gin: Book) -> None:
    a_run(gin, "GR-1", (500,) * 6)
    open_run(gin, "GR-2", "41207", date(2025, 10, 20))
    assert [item.run for item in season_control(gin, 2025)] == ["GR-1"]
