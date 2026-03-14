"""The account ledger: posting, reading back, and one settlement per run."""

from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from ginstand.errors import NotFoundError
from ginstand.model.account import Entry, EntryKind
from ginstand.model.ginrun import GinRun
from ginstand.model.producer import Producer
from ginstand.store.accounts import AccountStore
from ginstand.store.growers import ProducerStore
from ginstand.store.runs import RunStore
from ginstand.units.money import money

MADE = date(2025, 11, 3)


@pytest.fixture
def ledger(book: sqlite3.Connection) -> sqlite3.Connection:
    ProducerStore(book).add(Producer(ref="P-12", name="Aldys Brothers"))
    ProducerStore(book).add(Producer(ref="P-40", name="Merrick Land Co"))
    RunStore(book).add(
        GinRun(ref="GR-1", crop_year=2025, gin_code="41207", opened=date(2025, 10, 14))
    )
    RunStore(book).add(
        GinRun(ref="GR-2", crop_year=2025, gin_code="41207", opened=date(2025, 10, 20))
    )
    return book


def an_entry(**changes: object) -> Entry:
    fields: dict[str, object] = {
        "producer": "P-12",
        "crop_year": 2025,
        "made": MADE,
        "kind": EntryKind.SETTLEMENT,
        "amount": money("1000.00"),
        "run": "GR-1",
    }
    fields.update(changes)
    return Entry(**fields)  # type: ignore[arg-type]


def test_a_posted_entry_comes_back_with_an_id(ledger: sqlite3.Connection) -> None:
    store = AccountStore(ledger)
    posted = store.post(an_entry())
    assert posted.entry_id > 0
    assert store.get(posted.entry_id) == posted


def test_the_balance_adds_the_entries(ledger: sqlite3.Connection) -> None:
    store = AccountStore(ledger)
    assert store.balance("P-12", 2025) == 0
    store.post(an_entry())
    store.post(an_entry(kind=EntryKind.PAYMENT, amount=money("-400.00"), run=""))
    assert store.balance("P-12", 2025) == money("600.00")


def test_a_second_settlement_for_the_same_run_is_refused(
    ledger: sqlite3.Connection,
) -> None:
    store = AccountStore(ledger)
    store.post(an_entry())
    with pytest.raises(sqlite3.IntegrityError):
        store.post(an_entry(amount=money("50.00")))


def test_another_run_settles_to_the_same_producer(ledger: sqlite3.Connection) -> None:
    store = AccountStore(ledger)
    store.post(an_entry())
    store.post(an_entry(run="GR-2", amount=money("500.00")))
    assert store.balance("P-12", 2025) == money("1500.00")


def test_two_adjustments_against_one_run_are_fine(ledger: sqlite3.Connection) -> None:
    store = AccountStore(ledger)
    store.post(an_entry(kind=EntryKind.ADJUSTMENT, amount=money("10.00")))
    store.post(an_entry(kind=EntryKind.ADJUSTMENT, amount=money("20.00")))
    assert store.balance("P-12", 2025) == money("30.00")


def test_the_settlement_for_a_run_can_be_looked_up(ledger: sqlite3.Connection) -> None:
    store = AccountStore(ledger)
    assert store.settlement_for("P-12", "GR-1") is None
    store.post(an_entry())
    found = store.settlement_for("p-12", "gr-1")
    assert found is not None
    assert found.amount == money("1000.00")


def test_accounts_do_not_cross_producers_or_crop_years(
    ledger: sqlite3.Connection,
) -> None:
    store = AccountStore(ledger)
    store.post(an_entry())
    assert store.balance("P-40", 2025) == 0
    assert store.balance("P-12", 2026) == 0


def test_the_entries_read_back_oldest_first(ledger: sqlite3.Connection) -> None:
    store = AccountStore(ledger)
    store.post(an_entry(made=date(2025, 12, 1), run="GR-2"))
    store.post(an_entry())
    assert [entry.run for entry in store.entries("P-12", 2025)] == ["GR-1", "GR-2"]


def test_the_totals_split_by_kind(ledger: sqlite3.Connection) -> None:
    store = AccountStore(ledger)
    store.post(an_entry())
    store.post(an_entry(kind=EntryKind.ADJUSTMENT, amount=money("-40.00")))
    store.post(an_entry(kind=EntryKind.PAYMENT, amount=money("-500.00"), run=""))
    totals = store.totals("P-12", 2025)
    assert totals[EntryKind.SETTLEMENT] == money("1000.00")
    assert totals[EntryKind.ADJUSTMENT] == money("-40.00")
    assert totals[EntryKind.PAYMENT] == money("-500.00")


def test_a_kind_with_nothing_on_it_totals_zero(ledger: sqlite3.Connection) -> None:
    store = AccountStore(ledger)
    store.post(an_entry())
    assert store.totals("P-12", 2025)[EntryKind.PAYMENT] == 0


def test_the_producers_with_accounts_can_be_listed(
    ledger: sqlite3.Connection,
) -> None:
    store = AccountStore(ledger)
    store.post(an_entry())
    store.post(an_entry(producer="P-40", run="GR-2"))
    assert store.producers_with_entries(2025) == ("P-12", "P-40")
    assert store.producers_with_entries(2026) == ()


def test_a_days_postings_can_be_listed(ledger: sqlite3.Connection) -> None:
    store = AccountStore(ledger)
    store.post(an_entry())
    store.post(an_entry(producer="P-40", run="GR-2", made=date(2025, 12, 1)))
    assert [entry.producer for entry in store.posted_on(MADE)] == ["P-12"]


def test_an_entry_can_be_taken_off_again(ledger: sqlite3.Connection) -> None:
    store = AccountStore(ledger)
    posted = store.post(an_entry())
    store.remove(posted.entry_id)
    assert store.count() == 0
    assert store.balance("P-12", 2025) == 0


def test_removing_something_that_is_not_there_is_refused(
    ledger: sqlite3.Connection,
) -> None:
    with pytest.raises(NotFoundError, match="no account entry with reference 41"):
        AccountStore(ledger).remove(41)


def test_an_entry_against_a_producer_who_is_not_there_is_refused(
    ledger: sqlite3.Connection,
) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        AccountStore(ledger).post(an_entry(producer="P-99"))
