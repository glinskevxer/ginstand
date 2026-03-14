"""Posting to a producer's account, and reading what it comes to.

Working a settlement out and posting it are separate calls. A statement gets
printed and looked at before anybody agrees it, and a settlement that posted
itself the moment it was printed would mean a producer querying a figure had
already been credited with it.

Posting the same run twice is refused by the schema, and named here first so the
office is told which entry is in the way rather than shown a constraint.
"""

from __future__ import annotations

from datetime import date

from ginstand.charges.tariff import Tariff
from ginstand.errors import StateError
from ginstand.model.account import Entry, EntryKind
from ginstand.settle.statement import Statement, settle
from ginstand.store.book import Book
from ginstand.units.money import Money, format_money


def post_settlement(
    book: Book,
    run_ref: str,
    producer: str,
    tariff: Tariff,
    seed_price_per_ton: Money,
    on: date,
    extras: tuple[str, ...] = (),
) -> tuple[Statement, Entry]:
    """Work a statement out and put it on the producer's account."""
    statement = settle(book, run_ref, producer, tariff, seed_price_per_ton, on, extras)
    if statement.provisional:
        raise StateError(
            f"the statement for {statement.share.producer} on {statement.share.run} is "
            f"provisional, with {len(statement.share.unclassed)} bales unclassed"
        )
    standing = book.accounts.settlement_for(statement.share.producer, statement.share.run)
    if standing is not None:
        raise StateError(
            f"{statement.share.producer} was already settled for "
            f"{statement.share.run} on {standing.made.isoformat()} at "
            f"{format_money(standing.amount)}"
        )
    entry = book.accounts.post(
        Entry(
            producer=statement.share.producer,
            crop_year=statement.share.crop_year,
            made=on,
            kind=EntryKind.SETTLEMENT,
            amount=statement.total,
            run=statement.share.run,
            note=f"{statement.share.bales} bales",
        )
    )
    return statement, entry


def adjust(
    book: Book,
    producer: str,
    crop_year: int,
    amount: Money,
    on: date,
    note: str,
    run: str = "",
) -> Entry:
    """Put a correction on a producer's account."""
    who = book.producers.get(producer).ref
    if not note.strip():
        raise StateError("an adjustment needs a reason on it")
    if run:
        book.runs.get(run)
    return book.accounts.post(
        Entry(
            producer=who,
            crop_year=crop_year,
            made=on,
            kind=EntryKind.ADJUSTMENT,
            amount=amount,
            run=run,
            note=note,
        )
    )


def pay(
    book: Book,
    producer: str,
    crop_year: int,
    amount: Money,
    on: date,
    reference: str = "",
    note: str = "",
) -> Entry:
    """Record money going out to a producer.

    The amount is given as the producer sees it, so a payment is passed in
    positive and stored negative. Asking the office to type a minus sign on a
    cheque they just wrote is how a payment ends up doubling a balance.
    """
    who = book.producers.get(producer).ref
    if amount <= 0:
        raise StateError(f"a payment of {format_money(amount)} is not a payment")
    owed = book.accounts.balance(who, crop_year)
    if amount > owed:
        raise StateError(
            f"{who} is owed {format_money(owed)} for crop year {crop_year}, "
            f"and this pays {format_money(amount)}"
        )
    return book.accounts.post(
        Entry(
            producer=who,
            crop_year=crop_year,
            made=on,
            kind=EntryKind.PAYMENT,
            amount=Money(-amount),
            reference=reference,
            note=note,
        )
    )


def balance(book: Book, producer: str, crop_year: int) -> Money:
    """What the gin owes a producer for a crop year."""
    return book.accounts.balance(book.producers.get(producer).ref, crop_year)


def owing(book: Book, crop_year: int) -> dict[str, Money]:
    """Every producer the gin still owes, most owed first."""
    found = {
        producer: book.accounts.balance(producer, crop_year)
        for producer in book.accounts.producers_with_entries(crop_year)
    }
    return {
        producer: amount
        for producer, amount in sorted(found.items(), key=lambda item: -item[1])
        if amount != 0
    }
