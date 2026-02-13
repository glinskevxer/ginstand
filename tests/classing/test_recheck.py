"""A recheck is asked for inside the window, and the answer is read off the cards."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from ginstand.classing.filing import file_card, rechecks_closed_by
from ginstand.classing.recheck import (
    CHASE_AFTER_DAYS,
    differences,
    outstanding,
    request,
    settle,
    settle_from_card,
    to_chase,
)
from ginstand.errors import StateError
from ginstand.grades.color import ColorGrade
from ginstand.model.classing import Classing
from ginstand.model.recheck import RecheckOutcome, RecheckReason
from ginstand.store.book import Book

CLASSED = date(2025, 10, 22)
REQUESTED = date(2025, 10, 27)


def a_card(sequence: int = 61, **changes: object) -> Classing:
    fields: dict[str, object] = {
        "tag": f"2541207{sequence:05d}",
        "classed": CLASSED,
        "color": ColorGrade(31),
        "leaf": 3,
        "staple": 35,
        "micronaire": Decimal("4.3"),
        "strength": Decimal("29.4"),
        "uniformity": Decimal("81.2"),
    }
    fields.update(changes)
    return Classing(**fields)  # type: ignore[arg-type]


def test_a_recheck_needs_a_card_first(book: Book) -> None:
    with pytest.raises(StateError, match="has no card, so there is nothing to recheck"):
        request(book, "254120700061", RecheckReason.COLOUR, REQUESTED)


def test_a_recheck_is_sent_inside_the_window(book: Book) -> None:
    book.cards.add(a_card())
    sent = request(book, "254120700061", RecheckReason.COLOUR, REQUESTED, "R Ellis")
    assert sent.open
    assert sent.requested_by == "R Ellis"
    assert outstanding(book) == (sent,)


def test_a_recheck_past_the_window_names_the_last_day(book: Book) -> None:
    book.cards.add(a_card())
    with pytest.raises(StateError, match="only held to 2025-11-19"):
        request(book, "254120700061", RecheckReason.COLOUR, date(2025, 11, 20))


def test_a_recheck_before_the_card_is_refused(book: Book) -> None:
    book.cards.add(a_card())
    with pytest.raises(StateError, match="only held to"):
        request(book, "254120700061", RecheckReason.COLOUR, date(2025, 10, 21))


def test_a_second_open_recheck_names_the_one_out(book: Book) -> None:
    book.cards.add(a_card())
    request(book, "254120700061", RecheckReason.COLOUR, REQUESTED)
    with pytest.raises(StateError, match="already has a recheck out for colour"):
        request(book, "254120700061", RecheckReason.LEAF, date(2025, 10, 28))


def test_a_recheck_can_be_answered_by_hand(book: Book) -> None:
    book.cards.add(a_card())
    request(book, "254120700061", RecheckReason.COLOUR, REQUESTED)
    answered = settle(book, "254120700061", date(2025, 11, 3), RecheckOutcome.REFUSED, "gone")
    assert not answered.open
    assert answered.outcome is RecheckOutcome.REFUSED
    assert outstanding(book) == ()


def test_answering_a_bale_with_nothing_out_is_refused(book: Book) -> None:
    book.cards.add(a_card())
    with pytest.raises(StateError, match="has no recheck out"):
        settle(book, "254120700061", date(2025, 11, 3), RecheckOutcome.UNCHANGED)


def test_the_differences_between_two_cards_are_listed() -> None:
    before = a_card()
    after = a_card(leaf=2, color=ColorGrade(21))
    moved = differences(before, after)
    assert [item.reading for item in moved] == ["color", "leaf"]
    assert moved[0].text == "color 31 to 21"
    assert moved[1].text == "leaf 3 to 2"


def test_two_identical_cards_differ_in_nothing() -> None:
    assert differences(a_card(), a_card()) == ()


def test_trash_and_remarks_are_not_graded() -> None:
    before = a_card()
    after = a_card(trash_pct=Decimal("2.0"), remarks="looked again")
    assert differences(before, after) == ()


def test_a_recheck_card_that_moved_something_closes_it_as_changed(book: Book) -> None:
    book.cards.add(a_card())
    request(book, "254120700061", RecheckReason.LEAF, REQUESTED)
    answered = settle_from_card(
        book, a_card(), a_card(leaf=2, classed=date(2025, 11, 3)), date(2025, 11, 3)
    )
    assert answered is not None
    assert answered.outcome is RecheckOutcome.CHANGED
    assert answered.note == "leaf 3 to 2"


def test_a_recheck_card_that_moved_nothing_closes_it_as_unchanged(book: Book) -> None:
    book.cards.add(a_card())
    request(book, "254120700061", RecheckReason.LEAF, REQUESTED)
    answered = settle_from_card(book, a_card(), a_card(), date(2025, 11, 3))
    assert answered is not None
    assert answered.outcome is RecheckOutcome.UNCHANGED
    assert answered.note == ""


def test_a_card_for_a_bale_nobody_asked_about_closes_nothing(book: Book) -> None:
    book.cards.add(a_card())
    assert settle_from_card(book, a_card(), a_card(leaf=2), date(2025, 11, 3)) is None


def test_filing_a_recheck_closes_the_request(book: Book) -> None:
    book.cards.add(a_card())
    request(book, "254120700061", RecheckReason.LEAF, REQUESTED)
    assert file_card(book, a_card(leaf=2, classed=date(2025, 11, 3)), recheck=True) == "replaced"
    assert outstanding(book) == ()
    assert rechecks_closed_by(book, date(2025, 11, 3)) == 1


def test_filing_a_first_card_closes_nothing(book: Book) -> None:
    assert file_card(book, a_card()) == "filed"
    assert rechecks_closed_by(book, CLASSED) == 0


def test_a_request_out_too_long_is_one_to_chase(book: Book) -> None:
    book.cards.add(a_card())
    request(book, "254120700061", RecheckReason.COLOUR, REQUESTED)
    soon = REQUESTED + timedelta(days=CHASE_AFTER_DAYS)
    assert list(to_chase(book, soon)) == []
    late = soon + timedelta(days=1)
    assert len(list(to_chase(book, late))) == 1
