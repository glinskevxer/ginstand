"""One hold open per module at a time, and the schema is what keeps that true."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import NotFoundError
from ginstand.model.farm import Farm, Field
from ginstand.model.hold import Hold, HoldReason
from ginstand.model.module import Module, ModuleKind, WrapKind
from ginstand.model.producer import Lease, LeaseKind, Producer
from ginstand.store.growers import LeaseStore, ProducerStore
from ginstand.store.holds import HoldStore
from ginstand.store.land import FarmStore, FieldStore
from ginstand.store.modules import ModuleStore

PLACED = date(2025, 10, 3)


@pytest.fixture
def yard(book: sqlite3.Connection) -> sqlite3.Connection:
    ProducerStore(book).add(Producer(ref="P-12", name="Aldys Brothers"))
    LeaseStore(book).add(Lease(ref="L-1", tenant="P-12", kind=LeaseKind.OWNER))
    FarmStore(book).add(Farm(ref="F-3", producer="P-12", name="Home Place"))
    FieldStore(book).add(
        Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("78.4"), lease="L-1")
    )
    modules = ModuleStore(book)
    for tag in ("M-1", "M-2"):
        modules.add(
            Module(
                tag=tag,
                field="FL-9",
                kind=ModuleKind.RECTANGULAR,
                harvested=date(2025, 9, 30),
                received=date(2025, 10, 2),
                gross_pounds=48_200,
                tare_pounds=26_140,
                moisture_pct=Decimal("11.4"),
                wrap=WrapKind.TARP,
            )
        )
    return book


def test_a_placed_hold_comes_back_with_an_id(yard: sqlite3.Connection) -> None:
    store = HoldStore(yard)
    stored = store.place(Hold(module="M-1", reason=HoldReason.WET, placed=PLACED, placed_by="RE"))
    assert stored.hold_id > 0
    assert store.get(stored.hold_id) == stored


def test_the_open_hold_for_a_module_is_found(yard: sqlite3.Connection) -> None:
    store = HoldStore(yard)
    assert store.open_for("M-1") is None
    store.place(Hold(module="M-1", reason=HoldReason.PLASTIC, placed=PLACED))
    found = store.open_for("m-1")
    assert found is not None
    assert found.reason is HoldReason.PLASTIC


def test_a_second_open_hold_on_the_same_module_is_refused_by_the_schema(
    yard: sqlite3.Connection,
) -> None:
    store = HoldStore(yard)
    store.place(Hold(module="M-1", reason=HoldReason.WET, placed=PLACED))
    with pytest.raises(sqlite3.IntegrityError):
        store.place(Hold(module="M-1", reason=HoldReason.PLASTIC, placed=PLACED))


def test_a_module_can_be_held_again_once_the_first_hold_is_lifted(
    yard: sqlite3.Connection,
) -> None:
    store = HoldStore(yard)
    first = store.place(Hold(module="M-1", reason=HoldReason.WET, placed=PLACED))
    store.save(first.lift_on(date(2025, 10, 6), "JP"))
    second = store.place(Hold(module="M-1", reason=HoldReason.PLASTIC, placed=date(2025, 10, 8)))
    assert second.open
    assert len(store.history_for("M-1")) == 2


def test_a_hold_on_a_module_nobody_weighed_is_refused(yard: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        HoldStore(yard).place(Hold(module="M-9", reason=HoldReason.WET, placed=PLACED))


def test_lifting_writes_through_to_the_book(yard: sqlite3.Connection) -> None:
    store = HoldStore(yard)
    hold = store.place(Hold(module="M-1", reason=HoldReason.WET, placed=PLACED))
    store.save(hold.lift_on(date(2025, 10, 6), "J Pryor"))
    assert store.open_for("M-1") is None
    back = store.get(hold.hold_id)
    assert back.lifted == date(2025, 10, 6)
    assert back.lifted_by == "J Pryor"


def test_saving_a_hold_that_was_never_placed_is_refused(yard: sqlite3.Connection) -> None:
    store = HoldStore(yard)
    with pytest.raises(NotFoundError, match="no hold with reference 0"):
        store.save(Hold(module="M-1", reason=HoldReason.WET, placed=PLACED))
    with pytest.raises(NotFoundError, match="no hold with reference 99"):
        store.save(Hold(module="M-1", reason=HoldReason.WET, placed=PLACED, hold_id=99))


def test_the_history_for_a_module_reads_oldest_first(yard: sqlite3.Connection) -> None:
    store = HoldStore(yard)
    first = store.place(Hold(module="M-1", reason=HoldReason.WET, placed=PLACED))
    store.save(first.lift_on(date(2025, 10, 5)))
    store.place(Hold(module="M-1", reason=HoldReason.WEIGHT, placed=date(2025, 10, 9)))
    assert [h.reason for h in store.history_for("M-1")] == [HoldReason.WET, HoldReason.WEIGHT]


def test_every_open_hold_can_be_listed(yard: sqlite3.Connection) -> None:
    store = HoldStore(yard)
    store.place(Hold(module="M-1", reason=HoldReason.WET, placed=PLACED))
    store.place(Hold(module="M-2", reason=HoldReason.PLASTIC, placed=date(2025, 10, 1)))
    assert [h.module for h in store.all_open()] == ["M-2", "M-1"]


def test_what_was_open_on_a_day_reads_back_after_the_fact(yard: sqlite3.Connection) -> None:
    store = HoldStore(yard)
    hold = store.place(Hold(module="M-1", reason=HoldReason.WET, placed=PLACED))
    store.save(hold.lift_on(date(2025, 10, 6)))
    assert [h.module for h in store.open_on(date(2025, 10, 4))] == ["M-1"]
    assert store.open_on(date(2025, 10, 6)) == ()
    assert store.open_on(date(2025, 10, 2)) == ()


def test_a_hold_that_is_not_there_reads_as_missing(yard: sqlite3.Connection) -> None:
    store = HoldStore(yard)
    assert store.find(41) is None
    with pytest.raises(NotFoundError, match="no hold with reference 41"):
        store.get(41)
