"""What gins next.

Seed cotton sitting in a module goes off, and how fast it goes off depends on
how wet it is. A dry module can sit for a month. A module at twelve percent
cannot sit for a week. So the yard's order is not oldest first, and it is not
wettest first either: it is worst first, where worst is age multiplied by how
far above the safe moisture the module is.

That product is the whole idea. Moisture decides what age is worth, which is why
neither number on its own gives an order the gin manager agrees with.

The second rule is grouping. Once a producer's cotton is on the stands the yard
would rather finish it, because a run that mixes four producers has to be split
four ways afterwards and every split is a place to be wrong. Grouping is a
preference, not a rule: a module at risk still jumps the queue.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ginstand.errors import ValidationError
from ginstand.model.module import Module
from ginstand.store.book import Book
from ginstand.yard.holds import free_to_gin
from ginstand.yard.receiving import producer_of

SAFE_YARD_MOISTURE = Decimal("8.0")
"""At or below this a module can sit. Above it, every day costs something."""

RISK_LIMIT = Decimal("30.0")
"""Point days past which a module has to gin before anything comfortable does."""


def spoil_points(module: Module, on: date) -> Decimal:
    """Days in the yard multiplied by moisture above the safe line.

    Zero for anything at or under the safe moisture, however long it has sat.
    A dry module is not deteriorating and pretending it is would push real
    problems down the queue.
    """
    days = (on - module.received).days
    if days < 0:
        raise ValidationError("on", f"{on.isoformat()} is before the module was received")
    over = module.moisture_pct - SAFE_YARD_MOISTURE
    if over <= 0:
        return Decimal("0.0")
    return (Decimal(days) * over).quantize(Decimal("0.1"))


def at_risk(module: Module, on: date) -> bool:
    """Whether this module has to gin before anything comfortable does."""
    return spoil_points(module, on) >= RISK_LIMIT


@dataclass(frozen=True, slots=True)
class YardEntry:
    """One module's place in the queue, with the numbers that put it there."""

    tag: str
    producer: str
    received: date
    days_in_yard: int
    moisture_pct: Decimal
    points: Decimal
    at_risk: bool


def entry_for(book: Book, tag: str, on: date) -> YardEntry:
    """Work out one module's standing in the yard on a given day."""
    module = book.modules.get(tag)
    return YardEntry(
        tag=module.tag,
        producer=producer_of(book, module.tag),
        received=module.received,
        days_in_yard=(on - module.received).days,
        moisture_pct=module.moisture_pct,
        points=spoil_points(module, on),
        at_risk=at_risk(module, on),
    )


def _worst_first(entry: YardEntry) -> tuple[Decimal, date, str]:
    return (-entry.points, entry.received, entry.tag)


def queue(book: Book, tags: tuple[str, ...], on: date, group: bool = True) -> tuple[str, ...]:
    """The order these modules should gin in.

    Held modules are dropped rather than sorted to the back. A held module is not
    a low priority, it is not available, and a queue that lists it invites
    somebody to feed it.
    """
    available = free_to_gin(book, tags)
    entries = {tag: entry_for(book, tag, on) for tag in available}
    remaining = sorted(entries.values(), key=_worst_first)
    if not group:
        return tuple(entry.tag for entry in remaining)

    ordered: list[str] = []
    while remaining:
        head = remaining.pop(0)
        ordered.append(head.tag)
        if head.at_risk:
            continue
        same = [e for e in remaining if e.producer == head.producer and not e.at_risk]
        for entry in same:
            remaining.remove(entry)
            ordered.append(entry.tag)
    return tuple(ordered)


def yard_standing(book: Book, on: date) -> tuple[YardEntry, ...]:
    """Every unginned module, worst first, whether or not it is held."""
    entries = [entry_for(book, module.tag, on) for module in book.modules.unginned()]
    return tuple(sorted(entries, key=_worst_first))
