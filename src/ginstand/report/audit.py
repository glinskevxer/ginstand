"""Reading the whole book looking for things that cannot be true.

Every rule in this package refuses a bad write at the moment it is made. This is
for the state that no single write is wrong about: a closed run whose bales have
no owner, a receipt against a bale nobody was allocated, a crop year whose
carries do not cancel out. Each of those is made of writes that were all legal
when they happened.

A finding is not an error. It is something for a person to look at, and it says
what it found rather than what to do about it, because the answer is different
every time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from ginstand.report.table import Column, Table
from ginstand.store.book import Book
from ginstand.yard.order import RISK_LIMIT, spoil_points

LONG_RUN_DAYS = 7
"""A run open longer than this is one somebody forgot to close."""


class Severity(StrEnum):
    """How much a finding matters."""

    QUERY = "query"
    """Worth a look. Usually a run still in progress."""

    FAULT = "fault"
    """The book says two things that cannot both be true."""


@dataclass(frozen=True, slots=True)
class Note:
    """One thing the audit found."""

    severity: Severity
    subject: str
    message: str

    @property
    def line(self) -> str:
        """The note as the audit prints it."""
        return f"{self.severity:<6} {self.subject:<16} {self.message}"


def unallocated_closed_runs(book: Book) -> list[Note]:
    """Closed runs whose bales still belong to nobody."""
    notes = []
    for run in book.runs.list_all():
        if run.is_open or not book.bales.count_for_run(run.ref):
            continue
        if not book.allocations.run_is_allocated(run.ref):
            notes.append(
                Note(
                    Severity.FAULT,
                    run.ref,
                    f"closed on {run.closed} with "
                    f"{book.bales.count_for_run(run.ref)} bales and no allocation",
                )
            )
    return notes


def unowned_receipts(book: Book) -> list[Note]:
    """Receipts against bales that were never allocated."""
    return [
        Note(
            Severity.FAULT,
            receipt.number,
            f"is against bale {receipt.tag}, which has no owner",
        )
        for receipt in book.receipts.outstanding()
        if book.allocations.owner_of(receipt.tag) is None
    ]


def receipts_against_the_wrong_holder(book: Book) -> list[Note]:
    """Receipts whose holder is not a producer the book knows."""
    return [
        Note(Severity.FAULT, receipt.number, f"is held by {receipt.holder}, who is not in the book")
        for receipt in book.receipts.outstanding()
        if not book.producers.exists(receipt.holder)
    ]


def carries_that_do_not_cancel(book: Book) -> list[Note]:
    """Crop years whose allocation carries do not add back to zero.

    Every bale in a run goes to somebody, so what one producer is owed another
    has been given. The carries across a crop year therefore sum to zero, and a
    sum that does not is an allocation that went in by hand.
    """
    notes = []
    years = {run.crop_year for run in book.runs.list_all()}
    for year in sorted(years):
        carries = book.allocations.carries(year)
        if not carries:
            continue
        total = sum(carries.values(), Decimal("0"))
        if abs(total) > Decimal("0.000001"):
            notes.append(
                Note(Severity.FAULT, str(year), f"the carries add to {total}, not to zero")
            )
    return notes


def long_open_runs(book: Book, on: date) -> list[Note]:
    """Runs that have been open longer than a run should be."""
    return [
        Note(
            Severity.QUERY,
            run.ref,
            f"has been open since {run.opened}, which is {(on - run.opened).days} days",
        )
        for run in book.runs.open_runs()
        if (on - run.opened).days > LONG_RUN_DAYS
    ]


def modules_at_risk(book: Book, on: date) -> list[Note]:
    """Modules the yard should have ginned by now."""
    notes = []
    for module in book.modules.unginned():
        if module.received > on:
            continue
        points = spoil_points(module, on)
        if points >= RISK_LIMIT:
            notes.append(
                Note(
                    Severity.QUERY,
                    module.tag,
                    f"has {points} spoil points at {module.moisture_pct}% "
                    f"after {(on - module.received).days} days",
                )
            )
    return notes


def bales_waiting_on_a_card(book: Book) -> list[Note]:
    """How many bales have no classing card yet."""
    waiting = book.cards.unclassed_tags()
    if not waiting:
        return []
    return [Note(Severity.QUERY, "classing", f"{len(waiting)} bales have no card yet")]


def audit(book: Book, on: date) -> tuple[Note, ...]:
    """Everything the audit found, faults first."""
    notes = [
        *unallocated_closed_runs(book),
        *unowned_receipts(book),
        *receipts_against_the_wrong_holder(book),
        *carries_that_do_not_cancel(book),
        *long_open_runs(book, on),
        *modules_at_risk(book, on),
        *bales_waiting_on_a_card(book),
    ]
    return tuple(sorted(notes, key=lambda note: (note.severity is Severity.QUERY, note.subject)))


def audit_table(book: Book, on: date) -> Table:
    """The audit as a table."""
    notes = audit(book, on)
    return Table(
        title=f"Book audit at {on.isoformat()}",
        columns=(Column("severity"), Column("subject"), Column("finding")),
        rows=tuple((str(note.severity), note.subject, note.message) for note in notes),
        footers=(
            (
                "",
                "",
                f"{sum(1 for n in notes if n.severity is Severity.FAULT)} faults, "
                f"{sum(1 for n in notes if n.severity is Severity.QUERY)} queries",
            ),
        ),
        empty_note="the book is consistent",
    )


def faults(book: Book, on: date) -> tuple[Note, ...]:
    """Only the findings that are contradictions rather than questions."""
    return tuple(note for note in audit(book, on) if note.severity is Severity.FAULT)
