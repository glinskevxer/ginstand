"""A bale gets one owner, and the carry is per producer per crop year."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.model.bale import Bale
from ginstand.model.ginrun import GinRun
from ginstand.model.producer import Producer
from ginstand.store.allocations import AllocationStore
from ginstand.store.bales import BaleStore
from ginstand.store.growers import ProducerStore
from ginstand.store.runs import RunStore

PRESSED = date(2025, 10, 14)


@pytest.fixture
def ginned(book: sqlite3.Connection) -> sqlite3.Connection:
    ProducerStore(book).add(Producer(ref="P-12", name="Aldys Brothers"))
    ProducerStore(book).add(Producer(ref="P-40", name="Merrick Land Co"))
    RunStore(book).add(GinRun(ref="GR-1", crop_year=2025, gin_code="41207", opened=PRESSED))
    bales = BaleStore(book)
    for sequence in (1, 2, 3):
        bales.add(
            Bale(
                tag=f"2541207{sequence:05d}",
                run="GR-1",
                pressed=PRESSED,
                gross_pounds=512,
                tare_pounds=22,
                moisture_pct=Decimal("6.8"),
            )
        )
    return book


def test_an_unallocated_bale_has_no_owner(ginned: sqlite3.Connection) -> None:
    store = AllocationStore(ginned)
    assert store.owner_of("254120700001") is None
    with pytest.raises(NotFoundError, match="no bale allocation with reference"):
        store.require_owner("254120700001")


def test_assigning_gives_the_bale_an_owner(ginned: sqlite3.Connection) -> None:
    store = AllocationStore(ginned)
    store.assign("25-41207-00001", "p-12", "gr-1", PRESSED)
    assert store.owner_of("254120700001") == "P-12"
    assert store.require_owner("254120700001") == "P-12"


def test_a_bale_cannot_be_given_to_two_producers(ginned: sqlite3.Connection) -> None:
    store = AllocationStore(ginned)
    store.assign("254120700001", "P-12", "GR-1", PRESSED)
    with pytest.raises(DuplicateError, match="bale allocation 254120700001"):
        store.assign("254120700001", "P-40", "GR-1", PRESSED)


def test_allocating_a_bale_nobody_pressed_is_refused(ginned: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        AllocationStore(ginned).assign("254120799999", "P-12", "GR-1", PRESSED)


def test_allocating_to_a_producer_who_is_not_there_is_refused(
    ginned: sqlite3.Connection,
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        AllocationStore(ginned).assign("254120700001", "P-99", "GR-1", PRESSED)


def test_a_producers_bales_list_in_tag_order(ginned: sqlite3.Connection) -> None:
    store = AllocationStore(ginned)
    store.assign("254120700003", "P-12", "GR-1", PRESSED)
    store.assign("254120700001", "P-12", "GR-1", PRESSED)
    store.assign("254120700002", "P-40", "GR-1", PRESSED)
    assert store.bales_for("P-12") == ("254120700001", "254120700003")
    assert store.bales_for("P-40") == ("254120700002",)


def test_a_run_reads_back_as_tag_to_producer(ginned: sqlite3.Connection) -> None:
    store = AllocationStore(ginned)
    assert not store.run_is_allocated("GR-1")
    store.assign("254120700001", "P-12", "GR-1", PRESSED)
    store.assign("254120700002", "P-40", "GR-1", PRESSED)
    assert store.bales_for_run("gr-1") == {
        "254120700001": "P-12",
        "254120700002": "P-40",
    }
    assert store.run_is_allocated("GR-1")


def test_the_counts_for_a_run_add_up(ginned: sqlite3.Connection) -> None:
    store = AllocationStore(ginned)
    store.assign("254120700001", "P-12", "GR-1", PRESSED)
    store.assign("254120700002", "P-12", "GR-1", PRESSED)
    store.assign("254120700003", "P-40", "GR-1", PRESSED)
    assert store.counts_for_run("GR-1") == {"P-12": 2, "P-40": 1}


def test_a_producer_with_no_carry_is_owed_nothing(ginned: sqlite3.Connection) -> None:
    assert AllocationStore(ginned).carry_for("P-12", 2025) == Decimal("0")


def test_a_carry_is_written_and_read_back_at_its_places(
    ginned: sqlite3.Connection,
) -> None:
    store = AllocationStore(ginned)
    store.set_carry("P-12", 2025, Decimal("-0.416667"))
    assert store.carry_for("P-12", 2025) == Decimal("-0.416667")
    assert str(store.carry_for("P-12", 2025)) == "-0.416667"


def test_writing_a_carry_twice_replaces_it(ginned: sqlite3.Connection) -> None:
    store = AllocationStore(ginned)
    store.set_carry("P-12", 2025, Decimal("0.5"))
    store.set_carry("P-12", 2025, Decimal("0.25"))
    assert store.carry_for("P-12", 2025) == Decimal("0.25")


def test_carries_do_not_cross_crop_years(ginned: sqlite3.Connection) -> None:
    store = AllocationStore(ginned)
    store.set_carry("P-12", 2025, Decimal("0.5"))
    assert store.carry_for("P-12", 2026) == Decimal("0")


def test_a_whole_run_of_carries_can_be_written_at_once(
    ginned: sqlite3.Connection,
) -> None:
    store = AllocationStore(ginned)
    store.set_carries({"P-12": Decimal("0.4"), "P-40": Decimal("-0.4")}, 2025)
    assert store.carries(2025) == {"P-12": Decimal("0.4"), "P-40": Decimal("-0.4")}
    assert store.carries(2026) == {}
