"""Receiving names what went wrong, and the ticket carries whose load it was."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.store.book import Book
from ginstand.yard.receiving import (
    producer_of,
    receive,
    seed_cotton_by_producer,
    ticket_for,
)

from .conftest import a_module


def test_the_ticket_carries_the_producer_and_the_field_name(book: Book) -> None:
    ticket = receive(book, a_module("M-1"))
    assert ticket.producer == "P-12"
    assert ticket.producer_name == "Aldys Brothers"
    assert ticket.field_name == "North 80"
    assert ticket.farm == "F-3"


def test_receiving_puts_the_module_in_the_book(book: Book) -> None:
    receive(book, a_module("M-1"))
    assert book.modules.get("M-1").net_pounds == 22_060


def test_a_module_on_a_field_nobody_has_is_refused_by_name(book: Book) -> None:
    with pytest.raises(NotFoundError, match="no field with reference FL-99"):
        receive(book, a_module("M-1", field="FL-99"))
    assert not book.modules.exists("M-1")


def test_weighing_the_same_tag_twice_names_the_module(book: Book) -> None:
    receive(book, a_module("M-1"))
    with pytest.raises(DuplicateError, match="module M-1 is already in the book"):
        receive(book, a_module("M-1", gross_pounds=40_000))


def test_the_ticket_flags_a_wet_module(book: Book) -> None:
    ticket = receive(book, a_module("M-1", moisture_pct=Decimal("13.2")))
    assert ticket.wet
    assert not ticket.dry
    assert ticket.line.endswith("WET")


def test_the_ticket_flags_a_module_too_dry_to_gin(book: Book) -> None:
    ticket = receive(book, a_module("M-1", moisture_pct=Decimal("4.2")))
    assert ticket.dry
    assert not ticket.wet
    assert ticket.line.endswith("DRY")


def test_a_module_in_the_ginning_band_is_flagged_neither_way(book: Book) -> None:
    ticket = receive(book, a_module("M-1", moisture_pct=Decimal("7.0")))
    assert not ticket.wet
    assert not ticket.dry
    assert ticket.line.endswith("7.0%")


def test_the_printed_line_reads_as_the_scale_house_prints_it(book: Book) -> None:
    ticket = receive(book, a_module("M-1", moisture_pct=Decimal("7.0")))
    assert ticket.line == "M-1  Aldys Brothers  North 80  22,060 lb  7.0%"


def test_the_ticket_can_be_built_without_writing_anything(book: Book) -> None:
    ticket = ticket_for(book, a_module("M-1"))
    assert ticket.tag == "M-1"
    assert not book.modules.exists("M-1")


def test_the_producer_of_a_module_walks_field_to_farm_to_producer(book: Book) -> None:
    receive(book, a_module("M-1"))
    receive(book, a_module("M-2", field="FL-5"))
    assert producer_of(book, "M-1") == "P-12"
    assert producer_of(book, "M-2") == "P-40"


def test_asking_for_a_module_that_is_not_there_raises(book: Book) -> None:
    with pytest.raises(NotFoundError, match="no module with reference M-9"):
        producer_of(book, "M-9")


def test_seed_cotton_splits_by_whose_cotton_it_is(book: Book) -> None:
    receive(book, a_module("M-1", gross_pounds=48_200))
    receive(book, a_module("M-2", gross_pounds=44_000, field="FL-2"))
    receive(book, a_module("M-3", gross_pounds=50_100, field="FL-5"))
    totals = seed_cotton_by_producer(book, ("M-1", "M-2", "M-3"))
    assert totals == {"P-12": (48_200 - 26_140) + (44_000 - 26_140), "P-40": 50_100 - 26_140}


def test_splitting_no_modules_gives_nothing(book: Book) -> None:
    assert seed_cotton_by_producer(book, ()) == {}
