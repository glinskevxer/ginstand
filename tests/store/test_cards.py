"""A card cannot exist without its bale, and a recheck replaces it in place."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from ginstand.classing.color import ColorGrade
from ginstand.classing.matter import Extraneous, ExtraneousKind, ExtraneousLevel
from ginstand.errors import DuplicateError, NotFoundError
from ginstand.model.bale import Bale
from ginstand.model.classing import Classing
from ginstand.model.ginrun import GinRun
from ginstand.store.bales import BaleStore
from ginstand.store.cards import CardStore
from ginstand.store.runs import RunStore

PRESSED = date(2025, 10, 14)
CLASSED = date(2025, 10, 22)


@pytest.fixture
def ginned(book: sqlite3.Connection) -> sqlite3.Connection:
    RunStore(book).add(GinRun(ref="GR-1", crop_year=2025, gin_code="41207", opened=PRESSED))
    bales = BaleStore(book)
    for sequence in (61, 62, 63):
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


def a_card(sequence: int, **changes: object) -> Classing:
    fields: dict[str, object] = {
        "tag": f"2541207{sequence:05d}",
        "classed": CLASSED,
        "color": ColorGrade(31),
        "leaf": 3,
        "staple": 35,
        "micronaire": Decimal("4.3"),
        "strength": Decimal("29.4"),
        "uniformity": Decimal("81.2"),
        "trash_pct": Decimal("0.6"),
    }
    fields.update(changes)
    return Classing(**fields)  # type: ignore[arg-type]


def test_a_card_reads_back_exactly_as_it_arrived(ginned: sqlite3.Connection) -> None:
    store = CardStore(ginned)
    card = a_card(61, office="MEM", remarks="reclass requested")
    store.add(card)
    assert store.get("254120700061") == card


def test_the_extraneous_notes_survive_the_round_trip(ginned: sqlite3.Connection) -> None:
    store = CardStore(ginned)
    notes = (
        Extraneous(ExtraneousKind.BARK, ExtraneousLevel.HEAVY),
        Extraneous(ExtraneousKind.PLASTIC),
    )
    store.add(a_card(61, extraneous=notes))
    back = store.get("254120700061")
    assert back.extraneous == notes
    assert back.codes == "BK2 PL1"
    assert back.carries_plastic


def test_a_card_with_no_notes_reads_back_with_none(ginned: sqlite3.Connection) -> None:
    store = CardStore(ginned)
    store.add(a_card(61))
    assert store.get("254120700061").extraneous == ()


def test_a_card_against_a_bale_nobody_pressed_is_refused(
    ginned: sqlite3.Connection,
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        CardStore(ginned).add(a_card(999))


def test_a_second_card_against_the_same_bale_is_refused(ginned: sqlite3.Connection) -> None:
    store = CardStore(ginned)
    store.add(a_card(61))
    with pytest.raises(DuplicateError, match="classing card 254120700061"):
        store.add(a_card(61, leaf=4))


def test_a_recheck_replaces_the_card_in_place(ginned: sqlite3.Connection) -> None:
    store = CardStore(ginned)
    store.add(a_card(61, leaf=4))
    store.replace(a_card(61, leaf=2, classed=date(2025, 11, 3), remarks="recheck"))
    back = store.get("254120700061")
    assert back.leaf == 2
    assert back.classed == date(2025, 11, 3)
    assert back.remarks == "recheck"


def test_replacing_a_card_that_was_never_filed_is_refused(
    ginned: sqlite3.Connection,
) -> None:
    with pytest.raises(NotFoundError, match="no classing card with reference"):
        CardStore(ginned).replace(a_card(61))


def test_the_decimal_readings_keep_their_place(ginned: sqlite3.Connection) -> None:
    store = CardStore(ginned)
    store.add(a_card(61, micronaire=Decimal("4.0"), trash_pct=Decimal("0.0")))
    back = store.get("254120700061")
    assert str(back.micronaire) == "4.0"
    assert str(back.trash_pct) == "0.0"


def test_cards_list_for_one_run(ginned: sqlite3.Connection) -> None:
    store = CardStore(ginned)
    store.add(a_card(62))
    store.add(a_card(61))
    assert [c.tag[-5:] for c in store.for_run("GR-1")] == ["00061", "00062"]
    assert len(store.list_all()) == 2


def test_the_bales_still_waiting_on_a_card_can_be_listed(
    ginned: sqlite3.Connection,
) -> None:
    store = CardStore(ginned)
    assert len(store.unclassed_tags()) == 3
    store.add(a_card(62))
    assert store.unclassed_tags() == ("254120700061", "254120700063")


def test_a_card_that_is_not_there_reads_as_not_classed_yet(
    ginned: sqlite3.Connection,
) -> None:
    store = CardStore(ginned)
    assert store.find("254120700061") is None
    assert not store.exists("254120700061")
