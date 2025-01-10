"""The error types carry enough to build a message the gin office can act on."""

from __future__ import annotations

import pytest

from ginstand.errors import (
    DuplicateError,
    GinstandError,
    NotFoundError,
    ScheduleError,
    StateError,
    ValidationError,
)


def test_every_error_descends_from_the_base() -> None:
    for cls in (ValidationError, NotFoundError, DuplicateError, StateError, ScheduleError):
        assert issubclass(cls, GinstandError)
    assert issubclass(GinstandError, Exception)


def test_validation_error_names_the_field_in_the_message() -> None:
    exc = ValidationError("moisture", "must be between 0 and 25 percent")
    assert str(exc) == "moisture: must be between 0 and 25 percent"
    assert exc.field == "moisture"
    assert exc.message == "must be between 0 and 25 percent"


def test_not_found_error_names_the_kind_and_the_key() -> None:
    exc = NotFoundError("module", "M-4471")
    assert str(exc) == "no module with reference M-4471"
    assert exc.kind == "module"
    assert exc.key == "M-4471"


def test_duplicate_error_reads_as_a_statement_about_the_book() -> None:
    exc = DuplicateError("producer", "P-12")
    assert str(exc) == "producer P-12 is already in the book"
    assert exc.kind == "producer"
    assert exc.key == "P-12"


def test_state_and_schedule_errors_keep_the_message_they_were_given() -> None:
    assert str(StateError("gin run GR-9 is closed")) == "gin run GR-9 is closed"
    assert str(ScheduleError("no mic band covers 9.4")) == "no mic band covers 9.4"


@pytest.mark.parametrize(
    "exc",
    [
        ValidationError("staple", "must be a whole number of 32nds"),
        NotFoundError("bale", "26123450000001"),
        DuplicateError("field", "F-3"),
        StateError("already classed"),
        ScheduleError("crop year 2019 is not loaded"),
    ],
)
def test_errors_can_be_caught_as_the_base_type(exc: GinstandError) -> None:
    with pytest.raises(GinstandError):
        raise exc
