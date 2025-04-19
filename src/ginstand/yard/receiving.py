"""Taking a module in at the scale.

The store will refuse a module whose field is not in the book, but it refuses it
as a foreign key error, which tells the scale operator nothing. Receiving goes
through here so the refusal names the field, and so the ticket that comes back
carries the producer: the operator wants to know whose load they just weighed,
and that is two joins away from the module record.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.model.module import Module
from ginstand.store.book import Book
from ginstand.units.moisture import needs_drying, too_dry_to_gin
from ginstand.units.weight import format_pounds


@dataclass(frozen=True, slots=True)
class ScaleTicket:
    """What the scale house prints when a module is weighed in."""

    tag: str
    field: str
    field_name: str
    farm: str
    producer: str
    producer_name: str
    received: date
    net_pounds: int
    dry_pounds: int
    moisture_pct: Decimal
    wet: bool
    dry: bool

    @property
    def line(self) -> str:
        """The one line that goes on the printed ticket."""
        note = " WET" if self.wet else (" DRY" if self.dry else "")
        return (
            f"{self.tag}  {self.producer_name}  {self.field_name}  "
            f"{format_pounds(self.net_pounds)}  {self.moisture_pct}%{note}"
        )


def ticket_for(book: Book, module: Module) -> ScaleTicket:
    """Build the scale ticket for a module, resolving the field and producer."""
    plot = book.fields.find(module.field)
    if plot is None:
        raise NotFoundError("field", module.field)
    farm = book.farms.get(plot.farm)
    producer = book.producers.get(farm.producer)
    return ScaleTicket(
        tag=module.tag,
        field=plot.ref,
        field_name=plot.name,
        farm=farm.ref,
        producer=producer.ref,
        producer_name=producer.name,
        received=module.received,
        net_pounds=module.net_pounds,
        dry_pounds=module.dry_pounds,
        moisture_pct=module.moisture_pct,
        wet=needs_drying(module.moisture_pct),
        dry=too_dry_to_gin(module.moisture_pct),
    )


def receive(book: Book, module: Module) -> ScaleTicket:
    """Weigh a module in and hand back its ticket.

    Refuses a tag that is already in the book by name rather than by constraint,
    because the scale operator's next move is to check whether they scanned the
    same module twice, and a foreign key error does not tell them that.
    """
    if book.modules.exists(module.tag):
        raise DuplicateError("module", module.tag)
    ticket = ticket_for(book, module)
    book.modules.add(module)
    return ticket


def producer_of(book: Book, tag: str) -> str:
    """Which producer's cotton a module is, walking field to farm to producer."""
    module = book.modules.get(tag)
    plot = book.fields.get(module.field)
    return book.farms.get(plot.farm).producer


def seed_cotton_by_producer(book: Book, tags: tuple[str, ...]) -> dict[str, int]:
    """Pounds of seed cotton in a set of modules, split by whose it is.

    This is the input to every allocation in the ginning layer, so it lives here
    where the walk from module to producer already is.
    """
    totals: dict[str, int] = {}
    for tag in tags:
        module = book.modules.get(tag)
        owner = producer_of(book, tag)
        totals[owner] = totals.get(owner, 0) + module.net_pounds
    return totals
