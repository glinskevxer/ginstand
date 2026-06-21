"""One recheck open per bale, held by a partial index."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import NotFoundError
from ginstand.model.bale import Bale
from ginstand.model.ginrun import GinRun
from ginstand.model.recheck import Recheck, RecheckOutcome, RecheckReason
from ginstand.store.bales import BaleStore
from ginstand.store.rechecks import RecheckStore
from ginstand.store.runs import RunStore

PRESSED = date(2025, 10, 14)
REQUESTED = date(2025, 10, 27)


@pytest.fixture
def ginned(book: sqlite3.Connection) -> sqlite3.Connection:
    RunStore(book).add(GinRun(ref="GR-1", crop_year=2025, gin_code="41207", opened=PRESSED))
    bales = BaleStore(book)
    for sequence in (61, 62):
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


def a_request(sequence: int = 61, **changes: object) -> Recheck:
    fields: dict[str, object] = {
        "tag": f"2541207{sequence:05d}",
        "requested": REQUESTED,
        "reason": RecheckReason.COLOUR,
        "requested_by": "R Ellis",
    }
    fields.update(changes)
    return Recheck(**fields)  # type: ignore[arg-type]


def test_a_request_comes_back_with_an_id(ginned: sqlite3.Connection) -> None:
    store = RecheckStore(ginned)
    stored = store.request(a_request())
    assert stored.recheck_id > 0
    assert store.get(stored.recheck_id) == stored


def test_the_open_request_for_a_bale_is_found(ginned: sqlite3.Connection) -> None:
    store = RecheckStore(ginned)
    assert store.open_for("254120700061") is None
    store.request(a_request())
    found = store.open_for("25-41207-00061")
    assert found is not None
    assert found.reason is RecheckReason.COLOUR


def test_a_second_open_request_is_refused_by_the_schema(
    ginned: sqlite3.Connection,
) -> None:
    store = RecheckStore(ginned)
    store.request(a_request())
    with pytest.raises(sqlite3.IntegrityError):
        store.request(a_request(reason=RecheckReason.LEAF))


def test_a_bale_can_be_asked_about_again_once_the_first_is_answered(
    ginned: sqlite3.Connection,
) -> None:
    store = RecheckStore(ginned)
    first = store.request(a_request())
    store.save(first.settle_on(date(2025, 11, 3), RecheckOutcome.UNCHANGED))
    store.request(a_request(requested=date(2025, 11, 5), reason=RecheckReason.STAPLE))
    assert len(store.history_for("254120700061")) == 2


def test_a_request_against_a_bale_nobody_pressed_is_refused(
    ginned: sqlite3.Connection,
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        RecheckStore(ginned).request(a_request(999))


def test_settling_a_recheck_writes_through(ginned: sqlite3.Connection) -> None:
    store = RecheckStore(ginned)
    request = store.request(a_request())
    store.save(request.settle_on(date(2025, 11, 3), RecheckOutcome.CHANGED, "leaf 3 to 2"))
    assert store.open_for("254120700061") is None
    back = store.get(request.recheck_id)
    assert back.outcome is RecheckOutcome.CHANGED
    assert back.note == "leaf 3 to 2"


def test_saving_a_request_that_was_never_sent_is_refused(
    ginned: sqlite3.Connection,
) -> None:
    store = RecheckStore(ginned)
    with pytest.raises(NotFoundError, match="no recheck with reference 0"):
        store.save(a_request())
    with pytest.raises(NotFoundError, match="no recheck with reference 41"):
        store.save(a_request(recheck_id=41))


def test_every_open_request_can_be_listed(ginned: sqlite3.Connection) -> None:
    store = RecheckStore(ginned)
    store.request(a_request(61))
    store.request(a_request(62, requested=date(2025, 10, 25)))
    assert [r.tag[-5:] for r in store.all_open()] == ["00062", "00061"]


def test_the_answers_in_a_window_can_be_listed(ginned: sqlite3.Connection) -> None:
    store = RecheckStore(ginned)
    first = store.request(a_request(61))
    store.save(first.settle_on(date(2025, 11, 3), RecheckOutcome.CHANGED))
    second = store.request(a_request(62))
    store.save(second.settle_on(date(2025, 12, 1), RecheckOutcome.UNCHANGED))
    window = store.settled_between(date(2025, 11, 1), date(2025, 11, 30))
    assert [r.tag[-5:] for r in window] == ["00061"]


def test_a_request_that_is_not_there_reads_as_missing(
    ginned: sqlite3.Connection,
) -> None:
    store = RecheckStore(ginned)
    assert store.find(41) is None
    assert store.count() == 0
    with pytest.raises(NotFoundError, match="no recheck with reference 41"):
        store.get(41)
