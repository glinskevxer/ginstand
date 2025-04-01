"""A module goes into one run only, and positions are a gapless sequence."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.model.farm import Farm, Field
from ginstand.model.ginrun import GinRun
from ginstand.model.module import Module, ModuleKind, WrapKind
from ginstand.model.producer import Lease, LeaseKind, Producer
from ginstand.store.growers import LeaseStore, ProducerStore
from ginstand.store.land import FarmStore, FieldStore
from ginstand.store.modules import ModuleStore
from ginstand.store.runs import RunStore

OPENED = date(2025, 10, 14)


@pytest.fixture
def yard(book: sqlite3.Connection) -> sqlite3.Connection:
    ProducerStore(book).add(Producer(ref="P-12", name="Aldys Brothers"))
    LeaseStore(book).add(Lease(ref="L-1", tenant="P-12", kind=LeaseKind.OWNER))
    FarmStore(book).add(Farm(ref="F-3", producer="P-12", name="Home Place"))
    FieldStore(book).add(
        Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("78.4"), lease="L-1")
    )
    modules = ModuleStore(book)
    for tag, gross in (("M-1", 48_200), ("M-2", 44_000), ("M-3", 50_100)):
        modules.add(
            Module(
                tag=tag,
                field="FL-9",
                kind=ModuleKind.RECTANGULAR,
                harvested=date(2025, 9, 30),
                received=date(2025, 10, 2),
                gross_pounds=gross,
                tare_pounds=26_140,
                moisture_pct=Decimal("11.4"),
                wrap=WrapKind.TARP,
            )
        )
    RunStore(book).add(GinRun(ref="GR-1", crop_year=2025, gin_code="41207", opened=OPENED))
    return book


def test_a_run_reads_back_open(yard: sqlite3.Connection) -> None:
    run = RunStore(yard).get("gr-1")
    assert run.is_open
    assert run.opened == OPENED
    assert run.gin_code == "41207"


def test_a_closed_run_reads_back_closed(yard: sqlite3.Connection) -> None:
    runs = RunStore(yard)
    runs.save(runs.get("GR-1").close_on(date(2025, 10, 16)))
    assert runs.get("GR-1").closed == date(2025, 10, 16)
    assert runs.open_runs() == ()


def test_opening_the_same_reference_twice_is_refused(yard: sqlite3.Connection) -> None:
    with pytest.raises(DuplicateError, match="gin run GR-1 is already in the book"):
        RunStore(yard).add(GinRun(ref="GR-1", crop_year=2025, gin_code="41207", opened=OPENED))


def test_saving_a_run_that_is_not_there_is_refused(yard: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no gin run with reference GR-9"):
        RunStore(yard).save(GinRun(ref="GR-9", crop_year=2025, gin_code="41207", opened=OPENED))


def test_feeding_hands_out_positions_from_one(yard: sqlite3.Connection) -> None:
    runs = RunStore(yard)
    assert runs.next_position("GR-1") == 1
    assert runs.feed("GR-1", "M-1", OPENED) == 1
    assert runs.feed("GR-1", "M-2", OPENED) == 2
    assert runs.next_position("GR-1") == 3


def test_the_order_fed_is_the_order_read_back(yard: sqlite3.Connection) -> None:
    runs = RunStore(yard)
    runs.feed("GR-1", "M-3", OPENED)
    runs.feed("GR-1", "M-1", OPENED)
    runs.feed("GR-1", "M-2", OPENED)
    assert runs.modules_in("GR-1") == ("M-3", "M-1", "M-2")


def test_a_module_cannot_be_fed_into_two_runs(yard: sqlite3.Connection) -> None:
    runs = RunStore(yard)
    runs.add(GinRun(ref="GR-2", crop_year=2025, gin_code="41207", opened=OPENED))
    runs.feed("GR-1", "M-1", OPENED)
    with pytest.raises(DuplicateError, match="module M-1 is already in the book"):
        runs.feed("GR-2", "M-1", OPENED)


def test_a_module_cannot_be_fed_into_the_same_run_twice(yard: sqlite3.Connection) -> None:
    runs = RunStore(yard)
    runs.feed("GR-1", "M-1", OPENED)
    with pytest.raises(DuplicateError):
        runs.feed("GR-1", "M-1", OPENED)


def test_feeding_into_a_run_that_is_not_there_is_refused(yard: sqlite3.Connection) -> None:
    with pytest.raises(NotFoundError, match="no gin run with reference GR-9"):
        RunStore(yard).feed("GR-9", "M-1", OPENED)


def test_the_run_a_module_went_into_can_be_looked_up(yard: sqlite3.Connection) -> None:
    runs = RunStore(yard)
    assert runs.run_of("M-1") is None
    runs.feed("GR-1", "M-1", OPENED)
    assert runs.run_of("m-1") == "GR-1"


def test_a_module_in_a_run_drops_out_of_the_unginned_list(yard: sqlite3.Connection) -> None:
    RunStore(yard).feed("GR-1", "M-2", OPENED)
    assert [m.tag for m in ModuleStore(yard).unginned()] == ["M-1", "M-3"]


def test_the_seed_cotton_in_a_run_adds_the_module_nets(yard: sqlite3.Connection) -> None:
    runs = RunStore(yard)
    assert runs.seed_cotton_in("GR-1") == 0
    runs.feed("GR-1", "M-1", OPENED)
    runs.feed("GR-1", "M-2", OPENED)
    assert runs.seed_cotton_in("GR-1") == (48_200 - 26_140) + (44_000 - 26_140)


def test_runs_list_by_crop_year_and_by_open_state(yard: sqlite3.Connection) -> None:
    runs = RunStore(yard)
    runs.add(GinRun(ref="GR-2", crop_year=2025, gin_code="41207", opened=date(2025, 10, 20)))
    runs.add(GinRun(ref="GR-3", crop_year=2026, gin_code="41207", opened=date(2026, 9, 8)))
    assert [r.ref for r in runs.for_crop_year(2025)] == ["GR-1", "GR-2"]
    assert [r.ref for r in runs.list_all()] == ["GR-1", "GR-2", "GR-3"]
    runs.save(runs.get("GR-1").close_on(date(2025, 10, 16)))
    assert [r.ref for r in runs.open_runs()] == ["GR-2", "GR-3"]
