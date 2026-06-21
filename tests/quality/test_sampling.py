"""The run's size decides the sample, and the sample decides what fails."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import StateError, ValidationError
from ginstand.ginning.press import press
from ginstand.ginning.run import feed, open_run
from ginstand.model.farm import Farm, Field
from ginstand.model.module import Module, ModuleKind, WrapKind
from ginstand.model.producer import Lease, LeaseKind, Producer
from ginstand.quality.sampling import (
    TABLE,
    Plan,
    Verdict,
    explain,
    judge,
    plan_for,
    positions,
    sample_for,
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


def a_run(gin: Book, bales: int) -> None:
    open_run(gin, "GR-1", "41207", OPENED)
    receive(
        gin,
        Module(
            tag="M-1",
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
    feed(gin, "GR-1", "M-1", OPENED)
    for _ in range(bales):
        press(gin, "GR-1", OPENED, 512, 22, Decimal("6.8"))


def test_the_sample_grows_with_the_run() -> None:
    assert plan_for(4).sample == 2
    assert plan_for(30).sample == 5
    assert plan_for(100).sample == 13
    assert plan_for(400).sample == 32


def test_the_table_is_in_order_and_never_shrinks() -> None:
    lots = [rung.smallest_lot for rung in TABLE]
    samples = [rung.sample for rung in TABLE]
    assert lots == sorted(lots)
    assert samples == sorted(samples)


def test_a_lot_below_the_table_is_still_sampled() -> None:
    assert plan_for(1).sample == 2


def test_a_lot_with_no_bales_has_no_plan() -> None:
    with pytest.raises(ValidationError, match="at least one bale"):
        plan_for(0)


def test_a_bigger_sample_tolerates_one_failed_bale() -> None:
    assert plan_for(4).verdict(1) is Verdict.REJECT
    assert plan_for(30).verdict(1) is Verdict.ACCEPT
    assert plan_for(400).verdict(1) is Verdict.ACCEPT


def test_the_verdict_between_the_two_numbers_is_to_look_again() -> None:
    plan = plan_for(100)
    assert plan.accept == 2
    assert plan.reject == 4
    assert plan.verdict(2) is Verdict.ACCEPT
    assert plan.verdict(3) is Verdict.LOOK
    assert plan.verdict(4) is Verdict.REJECT


def test_a_count_that_cannot_have_happened_is_refused() -> None:
    plan = plan_for(30)
    with pytest.raises(ValidationError, match="must not be negative"):
        plan.verdict(-1)
    with pytest.raises(ValidationError, match="out of a sample of 5"):
        plan.verdict(6)


def test_a_plan_with_no_gap_between_its_numbers_is_refused() -> None:
    with pytest.raises(ValidationError, match="leaves nothing in between"):
        Plan(smallest_lot=1, sample=5, accept=2, reject=2)


def test_a_plan_that_cannot_fail_is_refused() -> None:
    with pytest.raises(ValidationError, match="cannot have 6 bad bales"):
        Plan(smallest_lot=1, sample=5, accept=1, reject=6)


def test_the_places_pulled_are_spread_across_the_run() -> None:
    places = positions(100, 5)
    assert len(places) == 5
    assert places[0] < 20
    assert places[-1] > 80
    assert list(places) == sorted(places)


def test_a_sample_as_big_as_the_run_takes_everything() -> None:
    assert positions(3, 5) == (1, 2, 3)
    assert positions(3, 3) == (1, 2, 3)


def test_a_sample_of_nothing_is_refused() -> None:
    with pytest.raises(ValidationError, match="at least one bale"):
        positions(10, 0)


def test_the_sample_names_real_bales(gin: Book) -> None:
    a_run(gin, 30)
    tags = sample_for(gin, "GR-1")
    assert len(tags) == plan_for(30).sample
    for tag in tags:
        assert gin.bales.exists(tag)


def test_a_run_with_no_bales_cannot_be_sampled(gin: Book) -> None:
    open_run(gin, "GR-1", "41207", OPENED)
    with pytest.raises(StateError, match="has pressed no bales"):
        sample_for(gin, "GR-1")
    with pytest.raises(StateError, match="has pressed no bales"):
        judge(gin, "GR-1", 0)


def test_the_verdict_comes_off_the_run_that_was_sampled(gin: Book) -> None:
    a_run(gin, 30)
    assert judge(gin, "GR-1", 1) is Verdict.ACCEPT
    assert judge(gin, "GR-1", 2) is Verdict.REJECT


def test_the_plan_prints_as_one_line() -> None:
    assert explain(100) == "100 bales: pull 13, accept on 2, reject on 4"
