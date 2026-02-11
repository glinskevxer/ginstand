"""A recheck is asked for while the sample is still held, and its answer is kept."""

from __future__ import annotations

from datetime import date

import pytest

from ginstand.errors import ValidationError
from ginstand.model.recheck import (
    SAMPLE_HELD_DAYS,
    Recheck,
    RecheckOutcome,
    RecheckReason,
    sample_held_until,
    within_window,
)

CLASSED = date(2025, 10, 22)
REQUESTED = date(2025, 10, 27)


def a_request(**changes: object) -> Recheck:
    fields: dict[str, object] = {
        "tag": "254120700061",
        "requested": REQUESTED,
        "reason": RecheckReason.COLOUR,
        "requested_by": "R Ellis",
    }
    fields.update(changes)
    return Recheck(**fields)  # type: ignore[arg-type]


def test_a_new_request_is_open() -> None:
    request = a_request()
    assert request.open
    assert request.outcome is RecheckOutcome.OPEN
    assert request.tag == "254120700061"


def test_an_open_request_cannot_carry_an_outcome() -> None:
    with pytest.raises(ValidationError, match="still open cannot be changed"):
        a_request(outcome=RecheckOutcome.CHANGED)


def test_a_settled_request_needs_an_outcome() -> None:
    with pytest.raises(ValidationError, match="needs an outcome"):
        a_request(settled=date(2025, 11, 3))


def test_a_request_settled_before_it_was_made_is_refused() -> None:
    with pytest.raises(ValidationError, match="before the request was made"):
        a_request(settled=date(2025, 10, 26), outcome=RecheckOutcome.UNCHANGED)


def test_settling_gives_back_an_answered_request() -> None:
    request = a_request()
    answered = request.settle_on(date(2025, 11, 3), RecheckOutcome.CHANGED, "leaf 3 to 2")
    assert request.open
    assert not answered.open
    assert answered.outcome is RecheckOutcome.CHANGED
    assert answered.note == "leaf 3 to 2"


def test_settling_twice_names_the_day_it_was_settled() -> None:
    answered = a_request(settled=date(2025, 11, 3), outcome=RecheckOutcome.UNCHANGED)
    with pytest.raises(ValidationError, match="settled on 2025-11-03"):
        answered.settle_on(date(2025, 11, 5), RecheckOutcome.CHANGED)


def test_settling_with_no_real_outcome_is_refused() -> None:
    with pytest.raises(ValidationError, match="needs a real outcome"):
        a_request().settle_on(date(2025, 11, 3), RecheckOutcome.OPEN)


def test_days_out_counts_to_today_while_it_is_open() -> None:
    assert a_request().days_out(date(2025, 11, 3)) == 7
    assert a_request().days_out(REQUESTED) == 0


def test_days_out_stops_at_the_answer() -> None:
    answered = a_request(settled=date(2025, 11, 3), outcome=RecheckOutcome.UNCHANGED)
    assert answered.days_out(date(2025, 12, 1)) == 7


def test_asking_before_the_request_is_refused() -> None:
    with pytest.raises(ValidationError, match="before the request"):
        a_request().days_out(date(2025, 10, 1))


def test_the_office_holds_a_sample_for_a_fixed_run_of_days() -> None:
    assert sample_held_until(CLASSED) == date(2025, 11, 19)
    assert (sample_held_until(CLASSED) - CLASSED).days == SAMPLE_HELD_DAYS


def test_the_window_is_inclusive_at_both_ends() -> None:
    assert within_window(CLASSED, CLASSED)
    assert within_window(CLASSED, sample_held_until(CLASSED))
    assert not within_window(CLASSED, date(2025, 11, 20))
    assert not within_window(CLASSED, date(2025, 10, 21))


def test_every_reason_and_outcome_reads_as_a_word() -> None:
    assert str(RecheckReason.EXTRANEOUS) == "extraneous matter"
    assert RecheckOutcome("refused") is RecheckOutcome.REFUSED
    assert len(set(RecheckReason)) == 6
    assert len(set(RecheckOutcome)) == 4
