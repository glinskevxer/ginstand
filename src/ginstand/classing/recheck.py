"""Asking for a recheck, and closing the request when the answer comes back.

Two rules decide whether a request can be made at all, and both of them are
about the sample rather than about the card. There has to be a card, because a
recheck is a second reading and not a first one. And the office has to still
have the sample, which it does for a fixed run of days from the date on the card.

Closing the request is the interesting half. When a recheck file is filed the
gin does not say whether anything changed, the two cards do, so the outcome is
worked out by comparing them rather than typed in. A request answered by a card
that reads the same is not a failure of the office, and a gin that records it as
one will never find out that its own classer is drifting.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, timedelta

from ginstand.errors import StateError
from ginstand.model.classing import Classing
from ginstand.model.recheck import (
    Recheck,
    RecheckOutcome,
    RecheckReason,
    sample_held_until,
    within_window,
)
from ginstand.store.book import Book

GRADED = ("color", "leaf", "staple", "micronaire", "strength", "uniformity")
"""The readings a recheck can change. Trash and remarks are not graded."""

CHASE_AFTER_DAYS = 14
"""A request out longer than this is one to ring the office about."""


@dataclass(frozen=True, slots=True)
class Difference:
    """One reading that the recheck moved."""

    reading: str
    before: str
    after: str

    @property
    def text(self) -> str:
        """The difference as it prints on a recheck report."""
        return f"{self.reading} {self.before} to {self.after}"


def differences(before: Classing, after: Classing) -> tuple[Difference, ...]:
    """Every graded reading the two cards disagree on."""
    found = []
    for reading in GRADED:
        was = getattr(before, reading)
        now = getattr(after, reading)
        if was != now:
            was_text = str(was.code) if reading == "color" else str(was)
            now_text = str(now.code) if reading == "color" else str(now)
            found.append(Difference(reading=reading, before=was_text, after=now_text))
    return tuple(found)


def request(
    book: Book,
    tag: str,
    reason: RecheckReason,
    on: date,
    by: str = "",
    note: str = "",
) -> Recheck:
    """Ask the office to read a sample again."""
    card = book.cards.find(tag)
    if card is None:
        raise StateError(
            f"bale {book.bales.get(tag).tag} has no card, so there is nothing to recheck"
        )
    standing = book.rechecks.open_for(card.tag)
    if standing is not None:
        raise StateError(
            f"bale {card.tag} already has a recheck out for {standing.reason} "
            f"since {standing.requested.isoformat()}"
        )
    if not within_window(card.classed, on):
        raise StateError(
            f"the sample for bale {card.tag} was classed on {card.classed.isoformat()} "
            f"and is only held to {sample_held_until(card.classed).isoformat()}"
        )
    return book.rechecks.request(
        Recheck(
            tag=card.tag,
            requested=on,
            reason=reason,
            requested_by=by,
            note=note,
        )
    )


def settle(book: Book, tag: str, on: date, outcome: RecheckOutcome, note: str = "") -> Recheck:
    """Answer an open request by hand."""
    standing = book.rechecks.open_for(tag)
    if standing is None:
        raise StateError(f"bale {book.bales.get(tag).tag} has no recheck out")
    answered = standing.settle_on(on, outcome, note)
    book.rechecks.save(answered)
    return answered


def settle_from_card(book: Book, before: Classing, after: Classing, on: date) -> Recheck | None:
    """Close a bale's open request from the card that came back.

    Returns None where there was no request out, because a recheck file can
    carry a card for a bale nobody asked about and that is not an error.
    """
    standing = book.rechecks.open_for(after.tag)
    if standing is None:
        return None
    moved = differences(before, after)
    outcome = RecheckOutcome.CHANGED if moved else RecheckOutcome.UNCHANGED
    note = ", ".join(item.text for item in moved)
    answered = standing.settle_on(on, outcome, note)
    book.rechecks.save(answered)
    return answered


def outstanding(book: Book) -> tuple[Recheck, ...]:
    """Every request the office still has."""
    return book.rechecks.all_open()


def to_chase(book: Book, on: date) -> Iterator[Recheck]:
    """Every request out longer than the office usually takes."""
    cutoff = on - timedelta(days=CHASE_AFTER_DAYS)
    for standing in book.rechecks.all_open():
        if standing.requested < cutoff:
            yield standing
