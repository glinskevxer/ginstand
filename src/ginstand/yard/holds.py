"""Placing and lifting holds, with the rules about when either is allowed.

Two rules live here rather than in the store. A module that has already been fed
into a run cannot be held, because holding it would say something about the
future that has already happened. And a hold cannot be placed on a module that
already has one open: the store's index refuses that as a constraint, and this
layer refuses it first with a message naming the hold that is in the way.

The suggestion is separate from the placing. The yard decides what to hold; this
only says what the ticket would justify holding.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ginstand.errors import StateError
from ginstand.model.hold import Hold, HoldReason
from ginstand.model.module import Module
from ginstand.store.book import Book

HOLD_MOISTURE = Decimal("14.0")
"""Past the dryers' range. A module this wet goes back out rather than through."""


def suggest(module: Module) -> HoldReason | None:
    """What the ticket alone would justify holding this module for.

    Wet beats plastic when both apply. A module that wet is not going anywhere
    today whatever else is wrong with it, and one reason on a hold is easier to
    lift cleanly than two.
    """
    if module.moisture_pct >= HOLD_MOISTURE:
        return HoldReason.WET
    return None


def open_hold(book: Book, module: str) -> Hold | None:
    """The module's open hold, or None."""
    return book.holds.open_for(module)


def held(book: Book, module: str) -> bool:
    """Whether a module is under an open hold."""
    return open_hold(book, module) is not None


def place(
    book: Book,
    module: str,
    reason: HoldReason,
    on: date,
    by: str = "",
    note: str = "",
) -> Hold:
    """Put a hold on a module in the yard."""
    record = book.modules.get(module)
    if book.runs.run_of(record.tag) is not None:
        raise StateError(
            f"module {record.tag} has already been ginned on run "
            f"{book.runs.run_of(record.tag)}, so it cannot be held"
        )
    existing = book.holds.open_for(record.tag)
    if existing is not None:
        raise StateError(
            f"module {record.tag} is already held for {existing.reason} "
            f"since {existing.placed.isoformat()}"
        )
    if on < record.received:
        raise StateError(
            f"a hold on {on.isoformat()} is before module {record.tag} was received "
            f"on {record.received.isoformat()}"
        )
    return book.holds.place(
        Hold(module=record.tag, reason=reason, placed=on, placed_by=by, note=note)
    )


def lift(book: Book, module: str, on: date, by: str = "") -> Hold:
    """Take the hold off a module."""
    record = book.modules.get(module)
    existing = book.holds.open_for(record.tag)
    if existing is None:
        raise StateError(f"module {record.tag} is not held")
    lifted = existing.lift_on(on, by)
    book.holds.save(lifted)
    return lifted


def free_to_gin(book: Book, tags: tuple[str, ...]) -> tuple[str, ...]:
    """The tags in ``tags`` that nothing is stopping, in the order given."""
    return tuple(tag for tag in tags if not held(book, tag))


def blocked(book: Book, tags: tuple[str, ...]) -> dict[str, HoldReason]:
    """The tags in ``tags`` that are held, and what they are held for."""
    found = {}
    for tag in tags:
        hold = open_hold(book, tag)
        if hold is not None:
            found[hold.module] = hold.reason
    return found
