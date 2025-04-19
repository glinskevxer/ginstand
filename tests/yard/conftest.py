"""A book with a gin's worth of grower records already in it."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from decimal import Decimal

import pytest

from ginstand.model.farm import Farm, Field
from ginstand.model.module import Module, ModuleKind, WrapKind
from ginstand.model.producer import Lease, LeaseKind, Producer
from ginstand.store.book import Book

DAY = date(2025, 8, 4)


@pytest.fixture
def book() -> Iterator[Book]:
    with Book.create(":memory:", DAY) as book:
        book.producers.add(Producer(ref="P-12", name="Aldys Brothers"))
        book.producers.add(Producer(ref="P-40", name="Merrick Land Co"))
        book.leases.add(Lease(ref="L-1", tenant="P-12", kind=LeaseKind.OWNER))
        book.leases.add(Lease(ref="L-3", tenant="P-40", kind=LeaseKind.OWNER))
        book.farms.add(Farm(ref="F-3", producer="P-12", name="Home Place"))
        book.farms.add(Farm(ref="F-7", producer="P-40", name="River Place"))
        book.fields.add(
            Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("78.4"), lease="L-1")
        )
        book.fields.add(
            Field(ref="FL-2", farm="F-3", name="Turnrow", acres=Decimal("30"), lease="L-1")
        )
        book.fields.add(
            Field(ref="FL-5", farm="F-7", name="Bend", acres=Decimal("55"), lease="L-3")
        )
        yield book


def a_module(tag: str, **changes: object) -> Module:
    fields: dict[str, object] = {
        "tag": tag,
        "field": "FL-9",
        "kind": ModuleKind.RECTANGULAR,
        "harvested": date(2025, 9, 30),
        "received": date(2025, 10, 2),
        "gross_pounds": 48_200,
        "tare_pounds": 26_140,
        "moisture_pct": Decimal("11.4"),
        "wrap": WrapKind.TARP,
    }
    fields.update(changes)
    return Module(**fields)  # type: ignore[arg-type]
