"""Modules are written once, read often, and corrected only on purpose."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.model.farm import Farm, Field
from ginstand.model.module import Module, ModuleKind, WrapKind
from ginstand.model.producer import Lease, LeaseKind, Producer
from ginstand.store.growers import LeaseStore, ProducerStore
from ginstand.store.land import FarmStore, FieldStore
from ginstand.store.modules import ModuleStore


@pytest.fixture
def yard(book: sqlite3.Connection) -> sqlite3.Connection:
    ProducerStore(book).add(Producer(ref="P-12", name="Aldys Brothers"))
    LeaseStore(book).add(Lease(ref="L-1", tenant="P-12", kind=LeaseKind.OWNER))
    FarmStore(book).add(Farm(ref="F-3", producer="P-12", name="Home Place"))
    FieldStore(book).add(
        Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("78.4"), lease="L-1")
    )
    FieldStore(book).add(
        Field(ref="FL-2", farm="F-3", name="Turnrow", acres=Decimal("30"), lease="L-1")
    )
    return book


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


def test_a_module_reads_back_exactly_as_it_was_weighed(yard: sqlite3.Connection) -> None:
    store = ModuleStore(yard)
    module = a_module("M-4471", variety="DP 2115", note="wet corner")
    store.add(module)
    assert store.get("m-4471") == module


def test_a_round_module_keeps_its_film_through_the_book(yard: sqlite3.Connection) -> None:
    store = ModuleStore(yard)
    store.add(a_module("M-1", kind=ModuleKind.ROUND, wrap=WrapKind.FILM))
    back = store.get("M-1")
    assert back.kind is ModuleKind.ROUND
    assert back.carries_plastic


def test_weighing_the_same_tag_twice_is_refused(yard: sqlite3.Connection) -> None:
    store = ModuleStore(yard)
    store.add(a_module("M-4471"))
    with pytest.raises(DuplicateError, match="module M-4471 is already in the book"):
        store.add(a_module("M-4471", gross_pounds=40_000))


def test_a_correction_replaces_the_ticket(yard: sqlite3.Connection) -> None:
    store = ModuleStore(yard)
    store.add(a_module("M-4471"))
    store.correct(a_module("M-4471", gross_pounds=48_600))
    assert store.get("M-4471").net_pounds == 22_460


def test_correcting_a_module_that_is_not_there_is_refused(yard: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no module with reference M-9"):
        ModuleStore(yard).correct(a_module("M-9"))


def test_a_module_naming_a_field_that_is_not_there_is_refused(
    yard: sqlite3.Connection,
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        ModuleStore(yard).add(a_module("M-1", field="FL-99"))


def test_modules_list_oldest_received_first(yard: sqlite3.Connection) -> None:
    store = ModuleStore(yard)
    store.add(a_module("M-3", received=date(2025, 10, 5)))
    store.add(a_module("M-1", received=date(2025, 10, 2)))
    store.add(a_module("M-2", received=date(2025, 10, 2)))
    assert [m.tag for m in store.list_all()] == ["M-1", "M-2", "M-3"]


def test_a_day_can_be_asked_for_on_its_own(yard: sqlite3.Connection) -> None:
    store = ModuleStore(yard)
    store.add(a_module("M-1", received=date(2025, 10, 2)))
    store.add(a_module("M-3", received=date(2025, 10, 5)))
    assert [m.tag for m in store.received_on(date(2025, 10, 2))] == ["M-1"]
    assert store.received_on(date(2025, 10, 4)) == ()


def test_modules_list_for_one_field(yard: sqlite3.Connection) -> None:
    store = ModuleStore(yard)
    store.add(a_module("M-1", field="FL-9"))
    store.add(a_module("M-2", field="FL-2"))
    assert [m.tag for m in store.for_field("fl-9")] == ["M-1"]


def test_everything_in_the_yard_is_unginned_until_a_run_takes_it(
    yard: sqlite3.Connection,
) -> None:
    store = ModuleStore(yard)
    store.add(a_module("M-1"))
    store.add(a_module("M-2"))
    assert [m.tag for m in store.unginned()] == ["M-1", "M-2"]


def test_the_seed_cotton_total_adds_the_nets(yard: sqlite3.Connection) -> None:
    store = ModuleStore(yard)
    assert store.seed_cotton_pounds() == 0
    store.add(a_module("M-1"))
    store.add(a_module("M-2", gross_pounds=44_000, tare_pounds=26_140))
    assert store.seed_cotton_pounds() == 22_060 + 17_860
