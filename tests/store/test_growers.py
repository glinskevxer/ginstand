"""Adding twice raises, updating something absent raises, and get and find differ."""

from __future__ import annotations

import sqlite3
from decimal import Decimal

import pytest

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.model.producer import Lease, LeaseKind, Producer
from ginstand.store.growers import LeaseStore, ProducerStore

ALDYS = Producer(ref="P-12", name="Aldys Brothers", phone="555 0143", ccc_number="A4471")
MERRICK = Producer(ref="P-40", name="Merrick Land Co")


def test_a_producer_reads_back_exactly_as_it_went_in(book: sqlite3.Connection) -> None:
    store = ProducerStore(book)
    store.add(ALDYS)
    assert store.get("P-12") == ALDYS
    assert store.get(" p-12 ") == ALDYS


def test_adding_the_same_reference_twice_is_refused(book: sqlite3.Connection) -> None:
    store = ProducerStore(book)
    store.add(ALDYS)
    with pytest.raises(DuplicateError, match="producer P-12 is already in the book"):
        store.add(Producer(ref="P-12", name="Somebody Else"))
    assert store.get("P-12").name == "Aldys Brothers"


def test_get_raises_where_find_returns_nothing(book: sqlite3.Connection) -> None:
    store = ProducerStore(book)
    assert store.find("P-99") is None
    assert not store.exists("P-99")
    with pytest.raises(NotFoundError, match="no producer with reference P-99"):
        store.get("P-99")


def test_updating_replaces_the_record_that_is_there(book: sqlite3.Connection) -> None:
    store = ProducerStore(book)
    store.add(ALDYS)
    store.update(Producer(ref="P-12", name="Aldys Bros", ccc_number="A4471"))
    assert store.get("P-12").name == "Aldys Bros"
    assert store.get("P-12").phone == ""


def test_updating_something_that_is_not_there_is_refused(book: sqlite3.Connection) -> None:
    store = ProducerStore(book)
    with pytest.raises(NotFoundError, match="no producer with reference P-12"):
        store.update(ALDYS)


def test_the_register_lists_in_reference_order(book: sqlite3.Connection) -> None:
    store = ProducerStore(book)
    store.add(MERRICK)
    store.add(ALDYS)
    assert [p.ref for p in store.list_all()] == ["P-12", "P-40"]


def test_an_empty_register_lists_nothing(book: sqlite3.Connection) -> None:
    assert ProducerStore(book).list_all() == ()


def test_a_lease_keeps_its_share_to_the_place_it_was_written(
    book: sqlite3.Connection,
) -> None:
    ProducerStore(book).add(ALDYS)
    leases = LeaseStore(book)
    lease = Lease(
        ref="L-2",
        tenant="P-12",
        kind=LeaseKind.SHARE,
        landlord="P-40",
        landlord_share=Decimal("0.2500"),
    )
    leases.add(lease)
    back = leases.get("L-2")
    assert back == lease
    assert str(back.landlord_share) == "0.2500"


def test_an_owner_lease_reads_back_with_no_landlord(book: sqlite3.Connection) -> None:
    ProducerStore(book).add(ALDYS)
    leases = LeaseStore(book)
    leases.add(Lease(ref="L-1", tenant="P-12", kind=LeaseKind.OWNER))
    back = leases.get("L-1")
    assert back.landlord == ""
    assert back.landlord_share == Decimal("0")
    assert not back.splits


def test_a_lease_naming_a_producer_who_is_not_in_the_book_is_refused(
    book: sqlite3.Connection,
) -> None:
    leases = LeaseStore(book)
    with pytest.raises(sqlite3.IntegrityError):
        leases.add(Lease(ref="L-1", tenant="P-99", kind=LeaseKind.OWNER))


def test_leases_can_be_listed_for_one_tenant(book: sqlite3.Connection) -> None:
    producers = ProducerStore(book)
    producers.add(ALDYS)
    producers.add(MERRICK)
    leases = LeaseStore(book)
    leases.add(Lease(ref="L-1", tenant="P-12", kind=LeaseKind.OWNER))
    leases.add(Lease(ref="L-3", tenant="P-40", kind=LeaseKind.OWNER))
    leases.add(
        Lease(
            ref="L-2",
            tenant="P-12",
            kind=LeaseKind.SHARE,
            landlord="P-40",
            landlord_share=Decimal("0.25"),
        )
    )
    assert [lease.ref for lease in leases.for_tenant("p-12")] == ["L-1", "L-2"]
    assert [lease.ref for lease in leases.list_all()] == ["L-1", "L-2", "L-3"]


def test_a_lease_that_is_not_there_behaves_like_any_other_missing_record(
    book: sqlite3.Connection,
) -> None:
    leases = LeaseStore(book)
    assert leases.find("L-9") is None
    with pytest.raises(NotFoundError, match="no lease with reference L-9"):
        leases.get("L-9")
    with pytest.raises(NotFoundError):
        leases.update(Lease(ref="L-9", tenant="P-12", kind=LeaseKind.OWNER))


def test_adding_a_lease_twice_is_refused(book: sqlite3.Connection) -> None:
    ProducerStore(book).add(ALDYS)
    leases = LeaseStore(book)
    lease = Lease(ref="L-1", tenant="P-12", kind=LeaseKind.OWNER)
    leases.add(lease)
    with pytest.raises(DuplicateError, match="lease L-1 is already in the book"):
        leases.add(lease)
