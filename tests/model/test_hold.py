"""A hold names who placed it and why, and it stays until somebody lifts it."""

from __future__ import annotations

from datetime import date

import pytest

from ginstand.errors import ValidationError
from ginstand.model.hold import Hold, HoldReason

PLACED = date(2025, 10, 3)


def a_hold(**changes: object) -> Hold:
    fields: dict[str, object] = {
        "module": "m-4471",
        "reason": HoldReason.WET,
        "placed": PLACED,
        "placed_by": "R Ellis",
    }
    fields.update(changes)
    return Hold(**fields)  # type: ignore[arg-type]


def test_a_hold_normalises_the_module_tag() -> None:
    assert a_hold().module == "M-4471"


def test_a_new_hold_is_open() -> None:
    hold = a_hold()
    assert hold.open
    assert hold.lifted is None
    assert hold.lifted_by == ""


def test_lifting_gives_back_a_lifted_hold_and_leaves_the_original() -> None:
    hold = a_hold()
    lifted = hold.lift_on(date(2025, 10, 9), "J Pryor")
    assert hold.open
    assert not lifted.open
    assert lifted.lifted == date(2025, 10, 9)
    assert lifted.lifted_by == "J Pryor"
    assert lifted.reason is HoldReason.WET


def test_lifting_a_lifted_hold_names_the_day_it_was_lifted() -> None:
    lifted = a_hold(lifted=date(2025, 10, 9))
    with pytest.raises(ValidationError, match="lifted on 2025-10-09"):
        lifted.lift_on(date(2025, 10, 10))


def test_a_hold_lifted_before_it_was_placed_is_refused() -> None:
    with pytest.raises(ValidationError, match="before the hold was placed"):
        a_hold(lifted=date(2025, 10, 2))


def test_an_open_hold_cannot_name_who_lifted_it() -> None:
    with pytest.raises(ValidationError, match="was not lifted by anyone"):
        a_hold(lifted_by="J Pryor")


def test_days_held_counts_to_today_while_the_hold_is_open() -> None:
    assert a_hold().days_held(date(2025, 10, 9)) == 6
    assert a_hold().days_held(PLACED) == 0


def test_days_held_stops_at_the_lift_once_it_is_lifted() -> None:
    lifted = a_hold(lifted=date(2025, 10, 9))
    assert lifted.days_held(date(2025, 11, 1)) == 6


def test_asking_how_long_before_it_was_placed_is_refused() -> None:
    with pytest.raises(ValidationError, match="before the hold was placed"):
        a_hold().days_held(date(2025, 10, 1))


def test_every_reason_reads_as_the_word_the_yard_uses() -> None:
    assert str(HoldReason.PLASTIC) == "plastic"
    assert HoldReason("identity") is HoldReason.IDENTITY
    assert len(set(HoldReason)) == 6


def test_a_hold_is_frozen() -> None:
    hold = a_hold()
    with pytest.raises(AttributeError):
        hold.reason = HoldReason.OTHER  # type: ignore[misc]
