"""Looking something up when all you have is what is written on it.

Somebody rings the gin holding a piece of paper with a number on it. They do not
know whether it is a module tag, a bale tag, a receipt or a producer number, and
telling them to work it out first is not an answer. So one search runs across
every register and says what it found and what kind of thing it is.

The search is a substring rather than an exact match, upper cased both sides,
because the number on the paper is usually part of the number in the book: a
bale tag written down as its last five digits, a producer number without its
prefix. Exact matching is what the individual stores are for.

Results are capped. A one character search matches most of the book and printing
it is not helping anybody, so it says how many it found and shows the first few.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from ginstand.errors import ValidationError
from ginstand.report.table import Column, Table
from ginstand.store.book import Book
from ginstand.units.weight import format_pounds

MINIMUM_SEARCH = 2
"""Below this a search matches everything, which is not a search."""

SHOWN = 25
"""How many results to print before saying how many more there are."""


@dataclass(frozen=True, slots=True)
class Hit:
    """One thing the search found."""

    kind: str
    reference: str
    description: str

    @property
    def line(self) -> str:
        """The line the search prints."""
        return f"{self.kind:<10} {self.reference:<14} {self.description}"


def _matches(needle: str, *fields: str) -> bool:
    return any(needle in (field or "").upper() for field in fields)


def _producers(book: Book, needle: str) -> Iterator[Hit]:
    for producer in book.producers.list_all():
        if _matches(needle, producer.ref, producer.name, producer.ccc_number):
            yield Hit("producer", producer.ref, producer.name)


def _land(book: Book, needle: str) -> Iterator[Hit]:
    for farm in book.farms.list_all():
        if _matches(needle, farm.ref, farm.name, farm.fsa_number):
            yield Hit("farm", farm.ref, f"{farm.name}, {farm.producer}")
    for plot in book.fields.list_all():
        if _matches(needle, plot.ref, plot.name, plot.variety):
            yield Hit("field", plot.ref, f"{plot.name}, {plot.acres} acres, {plot.farm}")


def _cotton(book: Book, needle: str) -> Iterator[Hit]:
    for module in book.modules.list_all():
        if _matches(needle, module.tag, module.variety, module.note):
            yield Hit(
                "module",
                module.tag,
                f"{format_pounds(module.net_pounds)} off {module.field}, "
                f"received {module.received.isoformat()}",
            )
    for run in book.runs.list_all():
        if _matches(needle, run.ref, run.shift, run.note):
            state = "open" if run.is_open else f"closed {run.closed}"
            yield Hit("gin run", run.ref, f"opened {run.opened}, {state}")
    for bale in book.bales.list_all():
        if _matches(needle, bale.tag):
            owner = book.allocations.owner_of(bale.tag) or "not allocated"
            yield Hit(
                "bale",
                bale.tag,
                f"{format_pounds(bale.net_pounds)} off {bale.run}, {owner}",
            )


def _kit(book: Book, needle: str) -> Iterator[Hit]:
    for receipt in book.receipts.list_all():
        if _matches(needle, receipt.number, receipt.tag):
            state = "outstanding" if receipt.outstanding else f"released {receipt.released}"
            yield Hit("receipt", receipt.number, f"bale {receipt.tag}, {state}")
    for house in book.warehouses.list_all():
        if _matches(needle, house.ref, house.name, house.code):
            yield Hit("warehouse", house.ref, house.name)
    for instrument in book.instruments.list_all():
        if _matches(needle, instrument.ref, instrument.description, instrument.serial):
            yield Hit(
                "instrument",
                instrument.ref,
                f"{instrument.description}, {instrument.kind}",
            )


def search(book: Book, text: str) -> tuple[Hit, ...]:
    """Everything in the book whose reference or name carries this text."""
    needle = text.strip().upper()
    if len(needle) < MINIMUM_SEARCH:
        raise ValidationError("search", f"needs at least {MINIMUM_SEARCH} characters, got {text!r}")
    return (
        *_producers(book, needle),
        *_land(book, needle),
        *_cotton(book, needle),
        *_kit(book, needle),
    )


def result_table(book: Book, text: str) -> Table:
    """What the search found, capped."""
    found = search(book, text)
    rows = tuple((hit.kind, hit.reference, hit.description) for hit in found[:SHOWN])
    more = len(found) - len(rows)
    return Table(
        title=f"Looking for {text.strip().upper()!r}: {len(found)} found"
        + (f", showing {SHOWN}" if more else ""),
        columns=(Column("kind"), Column("reference"), Column("what it is")),
        rows=rows,
        empty_note="nothing in the book carries that",
    )
