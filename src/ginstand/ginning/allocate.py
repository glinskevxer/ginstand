"""Handing a closed run's bales out to the producers who fed it.

Allocation happens once, after the run is closed, and it cannot be redone. That
is deliberate. The bales have physical tags on them by this point, the classing
office has samples keyed on those tags, and reallocating would mean the bale in
the warehouse belongs to somebody different from the bale on the last statement.

Which producer gets which bale is decided by press order against feed order.
Cotton comes off the stands in roughly the order it went in, so the first
producer's bales are the first bales pressed. It is an approximation and the
gin knows it is: what it buys is that a producer's bales tend to be the ones
made from their cotton, which is the difference between a lot that classes
consistently and one that does not.
"""

from __future__ import annotations

from datetime import date

from ginstand.errors import StateError
from ginstand.ginning.shares import Split, carries_from, split_bales
from ginstand.store.book import Book
from ginstand.yard.receiving import producer_of


def seed_cotton_in_feed_order(book: Book, run_ref: str) -> dict[str, int]:
    """Seed cotton by producer for a run, ordered by who fed first."""
    totals: dict[str, int] = {}
    for tag in book.runs.modules_in(run_ref):
        owner = producer_of(book, tag)
        totals[owner] = totals.get(owner, 0) + book.modules.get(tag).net_pounds
    return totals


def plan(book: Book, run_ref: str) -> Split:
    """Work out the split without writing anything."""
    run = book.runs.get(run_ref)
    weights = seed_cotton_in_feed_order(book, run.ref)
    if not weights:
        raise StateError(f"gin run {run.ref} has nothing in it to allocate")
    carry = {producer: book.allocations.carry_for(producer, run.crop_year) for producer in weights}
    return split_bales(book.bales.count_for_run(run.ref), weights, carry)


def allocate(book: Book, run_ref: str, on: date) -> Split:
    """Give the run's bales to its producers and record the carry that is left."""
    run = book.runs.get(run_ref)
    if run.is_open:
        raise StateError(f"gin run {run.ref} is still open, so its bales cannot be allocated")
    if book.allocations.run_is_allocated(run.ref):
        raise StateError(f"gin run {run.ref} has already been allocated")
    split = plan(book, run.ref)
    bales = book.bales.for_run(run.ref)
    if not bales:
        raise StateError(f"gin run {run.ref} pressed no bales, so there is nothing to allocate")

    handed = 0
    for share in split.shares:
        for bale in bales[handed : handed + share.bales]:
            book.allocations.assign(bale.tag, share.producer, run.ref, on)
        handed += share.bales
    book.allocations.set_carries(carries_from(split), run.crop_year)
    return split


def owner_of(book: Book, tag: str) -> str:
    """Which producer owns a bale. Raises if the run has not been allocated."""
    return book.allocations.require_owner(tag)


def bales_of(book: Book, producer: str) -> tuple[str, ...]:
    """Every bale tag a producer owns."""
    return book.allocations.bales_for(producer)


def unallocated_runs(book: Book, crop_year: int) -> tuple[str, ...]:
    """Closed runs in a crop year whose bales have not been handed out."""
    return tuple(
        run.ref
        for run in book.runs.for_crop_year(crop_year)
        if not run.is_open and not book.allocations.run_is_allocated(run.ref)
    )
