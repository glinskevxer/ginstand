"""The press: turning a run into numbered bales.

The bale number comes out of the book, not off a counter on the wall. That
matters more than it sounds like it should. The number is part of the permanent
bale identification, the classing office keys its cards on it, and a gin that
issues the same number twice in a crop year has two bales it cannot tell apart
for the rest of their lives.

A bale can only come off a run that is open. Once a run is closed its turnout
has been worked out and its bales allocated, and a late bale would change both
without anything downstream knowing.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ginstand.errors import StateError
from ginstand.ids import Pbi, make_pbi
from ginstand.model.bale import Bale
from ginstand.store.book import Book
from ginstand.units.moisture import moisture, safe_to_store


def next_tag(book: Book, run_ref: str) -> Pbi:
    """The tag the next bale off this run will carry."""
    run = book.runs.get(run_ref)
    last = book.bales.last_sequence(run.crop_year, run.gin_code)
    return make_pbi(run.crop_year, run.gin_code, last + 1)


def press(
    book: Book,
    run_ref: str,
    on: date,
    gross_pounds: int,
    tare_pounds: int,
    moisture_pct: Decimal,
    stand: str = "",
) -> Bale:
    """Take a bale off the press and give it the next tag in the crop year."""
    run = book.runs.get(run_ref)
    if not run.is_open:
        raise StateError(f"gin run {run.ref} closed on {run.closed}, so no bale can come off it")
    if not run.covers(on):
        raise StateError(
            f"{on.isoformat()} is outside gin run {run.ref}, which opened "
            f"on {run.opened.isoformat()}"
        )
    if not book.runs.modules_in(run.ref):
        raise StateError(f"gin run {run.ref} has no seed cotton in it yet")
    reading = moisture(moisture_pct, "bale moisture")
    if not safe_to_store(reading):
        raise StateError(
            f"a bale at {reading}% will heat in the warehouse, which is above the storage ceiling"
        )
    tag = next_tag(book, run.ref)
    bale = Bale(
        tag=tag.tag,
        run=run.ref,
        pressed=on,
        gross_pounds=gross_pounds,
        tare_pounds=tare_pounds,
        moisture_pct=reading,
        stand=stand,
    )
    book.bales.add(bale)
    return bale


def lint_off(book: Book, run_ref: str) -> int:
    """Net lint pressed off a run so far."""
    return book.bales.lint_pounds_for_run(book.runs.get(run_ref).ref)


def bale_count(book: Book, run_ref: str) -> int:
    """How many bales have come off a run."""
    return book.bales.count_for_run(book.runs.get(run_ref).ref)


def average_bale_weight(book: Book, run_ref: str) -> int:
    """Mean net weight of the bales off a run, rounded to the pound."""
    count = bale_count(book, run_ref)
    if count == 0:
        raise StateError(f"gin run {book.runs.get(run_ref).ref} has pressed no bales")
    return round(lint_off(book, run_ref) / count)
