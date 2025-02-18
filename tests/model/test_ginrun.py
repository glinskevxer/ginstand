"""A gin run is open until it is closed, and closing is what makes it final."""

from __future__ import annotations

from datetime import date

import pytest

from ginstand.errors import ValidationError
from ginstand.model.ginrun import GinRun


def a_run(**changes: object) -> GinRun:
    fields: dict[str, object] = {
        "ref": "gr-2025-04",
        "crop_year": 2025,
        "gin_code": "41207",
        "opened": date(2025, 10, 14),
    }
    fields.update(changes)
    return GinRun(**fields)  # type: ignore[arg-type]


def test_a_run_normalises_its_reference_and_checks_the_gin_code() -> None:
    run = a_run()
    assert run.ref == "GR-2025-04"
    assert run.gin_code == "41207"
    assert run.is_open


def test_a_run_opened_outside_its_crop_year_is_refused() -> None:
    with pytest.raises(ValidationError, match="outside crop year 2025"):
        a_run(opened=date(2025, 7, 31))


def test_a_run_may_open_on_the_first_day_of_the_crop_year() -> None:
    assert a_run(opened=date(2025, 8, 1)).opened == date(2025, 8, 1)


def test_a_run_closed_before_it_opened_is_refused() -> None:
    with pytest.raises(ValidationError, match="before the run opened"):
        a_run(closed=date(2025, 10, 13))


def test_a_run_closed_outside_its_crop_year_is_refused() -> None:
    with pytest.raises(ValidationError, match="outside crop year 2025"):
        a_run(closed=date(2026, 8, 2))


def test_closing_gives_back_a_closed_run_and_leaves_the_original_alone() -> None:
    run = a_run()
    closed = run.close_on(date(2025, 10, 15))
    assert run.is_open
    assert not closed.is_open
    assert closed.closed == date(2025, 10, 15)
    assert closed.ref == run.ref


def test_closing_a_closed_run_names_the_day_it_already_closed() -> None:
    closed = a_run(closed=date(2025, 10, 15))
    with pytest.raises(ValidationError, match="closed on 2025-10-15"):
        closed.close_on(date(2025, 10, 16))


def test_a_run_that_opened_and_closed_the_same_day_covered_one_day() -> None:
    assert a_run(closed=date(2025, 10, 14)).hours_span_days == 1
    assert a_run(closed=date(2025, 10, 16)).hours_span_days == 3


def test_an_open_run_has_no_span_yet() -> None:
    with pytest.raises(ValidationError, match="is still open"):
        assert a_run().hours_span_days


def test_an_open_run_covers_every_day_from_when_it_opened() -> None:
    run = a_run()
    assert not run.covers(date(2025, 10, 13))
    assert run.covers(date(2025, 10, 14))
    assert run.covers(date(2026, 1, 9))


def test_a_closed_run_stops_covering_after_it_closed() -> None:
    run = a_run(closed=date(2025, 10, 16))
    assert run.covers(date(2025, 10, 16))
    assert not run.covers(date(2025, 10, 17))


def test_the_crop_year_for_an_opening_day_is_offered_as_a_helper() -> None:
    assert GinRun.crop_year_for(date(2025, 10, 14)) == 2025
    assert GinRun.crop_year_for(date(2026, 1, 9)) == 2025


def test_a_bad_gin_code_is_caught_at_construction() -> None:
    with pytest.raises(ValidationError, match="must be 5 digits"):
        a_run(gin_code="4120")
