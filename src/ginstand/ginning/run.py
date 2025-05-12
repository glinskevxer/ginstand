"""Opening a run, feeding modules into it, and closing it.

A gin has one set of stands, so it has one run open at a time. That is enforced
here rather than left to the operator, because a second open run is not a
mistake anybody notices on the day: it shows up weeks later as a turnout figure
that cannot be reproduced, with modules split across two runs that were really
one.

Feeding checks five things, and every one of them has cost a gin somewhere a
disputed settlement: the run is open, the module exists, it is not held, it has
not already been ginned, and it was in the yard on the day it went in.
"""

from __future__ import annotations

from datetime import date

from ginstand.errors import StateError
from ginstand.ids import gin_code, reference
from ginstand.model.ginrun import GinRun
from ginstand.season import crop_year_of
from ginstand.store.book import Book
from ginstand.yard.holds import open_hold


def open_run(book: Book, ref: str, code: str, on: date, shift: str = "", note: str = "") -> GinRun:
    """Open a run. Refuses if one is already open."""
    already = book.runs.open_runs()
    if already:
        raise StateError(
            f"gin run {already[0].ref} is still open, close it before opening {reference(ref)}"
        )
    run = GinRun(
        ref=ref,
        crop_year=crop_year_of(on),
        gin_code=gin_code(code),
        opened=on,
        shift=shift,
        note=note,
    )
    book.runs.add(run)
    return run


def feed(book: Book, run_ref: str, module_tag: str, on: date) -> int:
    """Put a module into a run and return the position it took."""
    run = book.runs.get(run_ref)
    module = book.modules.get(module_tag)
    if not run.is_open:
        raise StateError(f"gin run {run.ref} closed on {run.closed}")
    if not run.covers(on):
        raise StateError(
            f"{on.isoformat()} is outside gin run {run.ref}, which opened "
            f"on {run.opened.isoformat()}"
        )
    hold = open_hold(book, module.tag)
    if hold is not None:
        raise StateError(
            f"module {module.tag} is held for {hold.reason} since {hold.placed.isoformat()}"
        )
    existing = book.runs.run_of(module.tag)
    if existing is not None:
        raise StateError(f"module {module.tag} was already ginned on run {existing}")
    if module.received > on:
        raise StateError(
            f"module {module.tag} was not received until {module.received.isoformat()}, "
            f"so it was not in the yard on {on.isoformat()}"
        )
    return book.runs.feed(run.ref, module.tag, on)


def feed_all(book: Book, run_ref: str, tags: tuple[str, ...], on: date) -> tuple[str, ...]:
    """Feed a queue of modules in the order given, and say what went in."""
    fed = []
    for tag in tags:
        feed(book, run_ref, tag, on)
        fed.append(reference(tag, "module tag"))
    return tuple(fed)


def close_run(book: Book, ref: str, on: date) -> GinRun:
    """Close a run so its turnout can be worked out."""
    run = book.runs.get(ref)
    if not run.is_open:
        raise StateError(f"gin run {run.ref} closed on {run.closed}")
    if not book.runs.modules_in(run.ref):
        raise StateError(f"gin run {run.ref} has nothing in it, so there is nothing to close")
    closed = run.close_on(on)
    book.runs.save(closed)
    return closed


def current_run(book: Book) -> GinRun | None:
    """The run that is open, or None if the gin is down."""
    runs = book.runs.open_runs()
    return runs[0] if runs else None


def require_open_run(book: Book) -> GinRun:
    """The run that is open. Raises if the gin is down."""
    run = current_run(book)
    if run is None:
        raise StateError("no gin run is open")
    return run
