"""Farms and fields read back whole, and the chain to the lease holds."""

from __future__ import annotations

import sqlite3
from decimal import Decimal

import pytest

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.model.farm import Farm, Field
from ginstand.model.producer import Lease, LeaseKind, Producer
from ginstand.store.growers import LeaseStore, ProducerStore
from ginstand.store.land import FarmStore, FieldStore


@pytest.fixture
def stood_up(book: sqlite3.Connection) -> sqlite3.Connection:
    ProducerStore(book).add(Producer(ref="P-12", name="Aldys Brothers"))
    ProducerStore(book).add(Producer(ref="P-40", name="Merrick Land Co"))
    LeaseStore(book).add(Lease(ref="L-1", tenant="P-12", kind=LeaseKind.OWNER))
    LeaseStore(book).add(
        Lease(
            ref="L-2",
            tenant="P-12",
            kind=LeaseKind.SHARE,
            landlord="P-40",
            landlord_share=Decimal("0.25"),
        )
    )
    return book


def test_a_farm_reads_back_exactly_as_it_went_in(stood_up: sqlite3.Connection) -> None:
    farms = FarmStore(stood_up)
    farm = Farm(ref="F-3", producer="P-12", name="Home Place", fsa_number="T4471", county="Bolivar")
    farms.add(farm)
    assert farms.get("f-3") == farm


def test_a_farm_naming_a_producer_who_is_not_there_is_refused(
    stood_up: sqlite3.Connection,
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        FarmStore(stood_up).add(Farm(ref="F-9", producer="P-99", name="Nowhere"))


def test_farms_list_for_one_producer(stood_up: sqlite3.Connection) -> None:
    farms = FarmStore(stood_up)
    farms.add(Farm(ref="F-3", producer="P-12", name="Home Place"))
    farms.add(Farm(ref="F-7", producer="P-40", name="River Place"))
    farms.add(Farm(ref="F-1", producer="P-12", name="Turnrow"))
    assert [f.ref for f in farms.for_producer("P-12")] == ["F-1", "F-3"]
    assert [f.ref for f in farms.list_all()] == ["F-1", "F-3", "F-7"]


def test_adding_and_updating_a_farm_follow_the_usual_rules(
    stood_up: sqlite3.Connection,
) -> None:
    farms = FarmStore(stood_up)
    farm = Farm(ref="F-3", producer="P-12", name="Home Place")
    with pytest.raises(NotFoundError):
        farms.update(farm)
    farms.add(farm)
    with pytest.raises(DuplicateError):
        farms.add(farm)
    farms.update(Farm(ref="F-3", producer="P-12", name="Home Place North"))
    assert farms.get("F-3").name == "Home Place North"


def test_a_field_keeps_its_acres_to_two_places(stood_up: sqlite3.Connection) -> None:
    FarmStore(stood_up).add(Farm(ref="F-3", producer="P-12", name="Home Place"))
    fields = FieldStore(stood_up)
    plot = Field(
        ref="FL-9",
        farm="F-3",
        name="North 80",
        acres=Decimal("78.40"),
        lease="L-2",
        variety="DP 2115",
        irrigated=True,
    )
    fields.add(plot)
    back = fields.get("fl-9")
    assert back == plot
    assert str(back.acres) == "78.40"
    assert back.irrigated is True


def test_a_field_that_is_not_irrigated_reads_back_as_false(
    stood_up: sqlite3.Connection,
) -> None:
    FarmStore(stood_up).add(Farm(ref="F-3", producer="P-12", name="Home Place"))
    fields = FieldStore(stood_up)
    fields.add(Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("40"), lease="L-1"))
    assert fields.get("FL-9").irrigated is False


def test_fields_list_by_farm_and_by_lease(stood_up: sqlite3.Connection) -> None:
    FarmStore(stood_up).add(Farm(ref="F-3", producer="P-12", name="Home Place"))
    FarmStore(stood_up).add(Farm(ref="F-7", producer="P-40", name="River Place"))
    fields = FieldStore(stood_up)
    fields.add(Field(ref="FL-2", farm="F-3", name="Turnrow", acres=Decimal("30"), lease="L-1"))
    fields.add(Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("78"), lease="L-2"))
    fields.add(Field(ref="FL-5", farm="F-7", name="Bend", acres=Decimal("55"), lease="L-2"))
    assert [f.ref for f in fields.for_farm("F-3")] == ["FL-2", "FL-9"]
    assert [f.ref for f in fields.for_lease("L-2")] == ["FL-5", "FL-9"]


def test_a_field_naming_a_lease_that_is_not_there_is_refused(
    stood_up: sqlite3.Connection,
) -> None:
    FarmStore(stood_up).add(Farm(ref="F-3", producer="P-12", name="Home Place"))
    with pytest.raises(sqlite3.IntegrityError):
        FieldStore(stood_up).add(
            Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("40"), lease="L-99")
        )


def test_a_missing_field_behaves_like_every_other_missing_record(
    stood_up: sqlite3.Connection,
) -> None:
    fields = FieldStore(stood_up)
    assert fields.find("FL-9") is None
    assert not fields.exists("FL-9")
    with pytest.raises(NotFoundError, match="no field with reference FL-9"):
        fields.get("FL-9")


def test_a_farm_lists_for_a_producer_who_has_none(stood_up: sqlite3.Connection) -> None:
    assert FarmStore(stood_up).for_producer("P-40") == ()


def test_a_field_can_be_updated_in_place(stood_up: sqlite3.Connection) -> None:
    FarmStore(stood_up).add(Farm(ref="F-3", producer="P-12", name="Home Place"))
    fields = FieldStore(stood_up)
    fields.add(Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("78.4"), lease="L-1"))
    fields.update(
        Field(
            ref="FL-9",
            farm="F-3",
            name="North 80",
            acres=Decimal("80"),
            lease="L-2",
            variety="DP 2115",
            irrigated=True,
        )
    )
    back = fields.get("FL-9")
    assert back.acres == Decimal("80.00")
    assert back.lease == "L-2"
    assert back.variety == "DP 2115"
    assert back.irrigated is True


def test_updating_a_field_that_is_not_there_is_refused(
    stood_up: sqlite3.Connection,
) -> None:
    FarmStore(stood_up).add(Farm(ref="F-3", producer="P-12", name="Home Place"))
    with pytest.raises(NotFoundError, match="no field with reference FL-9"):
        FieldStore(stood_up).update(
            Field(ref="FL-9", farm="F-3", name="North 80", acres=Decimal("40"), lease="L-1")
        )
