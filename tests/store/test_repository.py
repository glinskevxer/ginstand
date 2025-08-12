"""What every store gets from the base, checked once rather than eight times."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import NotFoundError
from ginstand.model.bale import Bale
from ginstand.model.farm import Farm, Field
from ginstand.model.ginrun import GinRun
from ginstand.model.module import Module, ModuleKind, WrapKind
from ginstand.model.producer import Lease, LeaseKind, Producer
from ginstand.store.bales import BaleStore
from ginstand.store.cards import CardStore
from ginstand.store.growers import LeaseStore, ProducerStore
from ginstand.store.land import FarmStore, FieldStore
from ginstand.store.modules import ModuleStore
from ginstand.store.repository import Repository
from ginstand.store.runs import RunStore

DAY = date(2025, 10, 14)

STORES = (
    ProducerStore,
    LeaseStore,
    FarmStore,
    FieldStore,
    ModuleStore,
    RunStore,
    BaleStore,
    CardStore,
)


@pytest.mark.parametrize("store_class", STORES)
def test_every_store_is_a_repository(store_class: type[Repository[object]]) -> None:
    assert issubclass(store_class, Repository)
    assert store_class.table
    assert store_class.kind
    assert store_class.order_by


@pytest.mark.parametrize("store_class", STORES)
def test_every_store_names_a_table_that_is_in_the_schema(
    store_class: type[Repository[object]], book: sqlite3.Connection
) -> None:
    from ginstand.store.sqlite import table_names

    assert store_class.table in table_names(book)


@pytest.mark.parametrize("store_class", STORES)
def test_every_store_counts_an_empty_book_as_empty(
    store_class: type[Repository[object]], book: sqlite3.Connection
) -> None:
    store = store_class(book)
    assert store.count() == 0
    assert store.list_all() == ()


def test_the_missing_record_message_uses_each_store_s_own_word(
    book: sqlite3.Connection,
) -> None:
    with pytest.raises(NotFoundError, match="no producer with reference P-9"):
        ProducerStore(book).get("P-9")
    with pytest.raises(NotFoundError, match="no gin run with reference GR-9"):
        RunStore(book).get("GR-9")
    with pytest.raises(NotFoundError, match="no classing card with reference"):
        CardStore(book).get("254120700061")


def test_the_bale_stores_normalise_a_tag_the_way_a_tag_is_written(
    book: sqlite3.Connection,
) -> None:
    RunStore(book).add(GinRun(ref="GR-1", crop_year=2025, gin_code="41207", opened=DAY))
    BaleStore(book).add(
        Bale(
            tag="254120700061",
            run="GR-1",
            pressed=DAY,
            gross_pounds=512,
            tare_pounds=22,
            moisture_pct=Decimal("6.8"),
        )
    )
    for written in ("254120700061", "25-41207-00061", " 25 41207 00061 "):
        assert BaleStore(book).exists(written)


def test_the_module_store_hands_records_back_oldest_first(
    book: sqlite3.Connection,
) -> None:
    ProducerStore(book).add(Producer(ref="P-1", name="Aldys"))
    LeaseStore(book).add(Lease(ref="L-1", tenant="P-1", kind=LeaseKind.OWNER))
    FarmStore(book).add(Farm(ref="F-1", producer="P-1", name="Home"))
    FieldStore(book).add(
        Field(ref="FL-1", farm="F-1", name="North", acres=Decimal("40"), lease="L-1")
    )
    modules = ModuleStore(book)
    for tag, received in (("M-3", date(2025, 10, 5)), ("M-1", date(2025, 10, 2))):
        modules.add(
            Module(
                tag=tag,
                field="FL-1",
                kind=ModuleKind.RECTANGULAR,
                harvested=date(2025, 9, 30),
                received=received,
                gross_pounds=48_200,
                tare_pounds=26_140,
                moisture_pct=Decimal("9.4"),
                wrap=WrapKind.TARP,
            )
        )
    assert [m.tag for m in modules.list_all()] == ["M-1", "M-3"]
    assert modules.count() == 2
