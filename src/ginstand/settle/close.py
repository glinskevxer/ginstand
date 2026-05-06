"""Closing a crop year, and settling the fractions of a bale nobody got.

Through the season a producer who is owed part of a bale carries it to their
next run. At the end of the year there is no next run, so the fraction has to be
paid. It is paid in lint: the fraction multiplied by the season's mean bale
weight, valued at the season's mean loan rate.

Both of those means are the season's, not the producer's own. A producer owed a
third of a bale did not grow a third of a bale, they are owed a third of what a
bale off this gin was worth this year, and the gin's own average is the only
figure both sides can check.

Closing is refused while anything is unfinished. A crop year with a run still
open, or one closed and never allocated, has carries that are not final, and
paying a carry that is going to move is worse than paying it late.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from ginstand.errors import NotFoundError, StateError
from ginstand.ginning.season import totals
from ginstand.loan.schedule import schedule_for
from ginstand.loan.value import value_bale
from ginstand.model.account import Entry, EntryKind
from ginstand.store.book import Book
from ginstand.store.sqlite import as_date, as_decimal
from ginstand.units.money import Money, at_rate, format_money


@dataclass(frozen=True, slots=True)
class Closing:
    """A crop year, closed."""

    crop_year: int
    closed_on: date
    bale_weight: int
    rate: Decimal
    note: str = ""

    @property
    def line(self) -> str:
        """The line the close prints."""
        return (
            f"crop year {self.crop_year} closed {self.closed_on.isoformat()}  "
            f"{self.bale_weight} lb a bale at {self.rate}c"
        )

    def value_of(self, carry: Decimal) -> Money:
        """What a fraction of a bale is worth at this year's figures."""
        pounds = (Decimal(self.bale_weight) * carry).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return (
            Money(-at_rate(int(-pounds), self.rate))
            if pounds < 0
            else at_rate(int(pounds), self.rate)
        )


def closing_for(book: Book, crop_year: int) -> Closing | None:
    """The record of a crop year's close, or None if it is still open."""
    row = book.connection.execute(
        "SELECT * FROM crop_year_close WHERE crop_year = ?", (crop_year,)
    ).fetchone()
    if row is None:
        return None
    return Closing(
        crop_year=int(row["crop_year"]),
        closed_on=as_date(row["closed_on"]),
        bale_weight=int(row["bale_weight"]),
        rate=as_decimal(row["rate"]),
        note=str(row["note"]),
    )


def is_closed(book: Book, crop_year: int) -> bool:
    """Whether a crop year has been closed."""
    return closing_for(book, crop_year) is not None


def unfinished(book: Book, crop_year: int) -> tuple[str, ...]:
    """Every reason a crop year cannot be closed yet."""
    reasons = []
    for run in book.runs.for_crop_year(crop_year):
        if run.is_open:
            reasons.append(f"gin run {run.ref} is still open")
        elif book.bales.count_for_run(run.ref) and not book.allocations.run_is_allocated(run.ref):
            reasons.append(f"gin run {run.ref} has not been allocated")
    return tuple(reasons)


def mean_rate(book: Book, crop_year: int) -> Decimal:
    """The season's mean loan rate over the bales the loan would take."""
    schedule = schedule_for(crop_year)
    value = 0
    pounds = 0
    for card in book.cards.list_all():
        bale = book.bales.get(card.tag)
        if bale.crop_year != crop_year:
            continue
        valuation = value_bale(schedule, card, bale.net_pounds)
        if valuation.eligible:
            value += valuation.value
            pounds += bale.net_pounds
    if pounds == 0:
        return Decimal("0.0000")
    return (Decimal(value) / pounds).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def close(
    book: Book, crop_year: int, on: date, note: str = ""
) -> tuple[Closing, tuple[Entry, ...]]:
    """Close a crop year and pay out the fractions of a bale that are left."""
    if is_closed(book, crop_year):
        raise StateError(f"crop year {crop_year} was already closed")
    reasons = unfinished(book, crop_year)
    if reasons:
        raise StateError(f"crop year {crop_year} is not finished: {'; '.join(reasons)}")
    season = totals(book, crop_year)
    if season.bales == 0:
        raise StateError(f"crop year {crop_year} pressed no bales")

    closing = Closing(
        crop_year=crop_year,
        closed_on=on,
        bale_weight=season.lint_per_bale,
        rate=mean_rate(book, crop_year),
        note=note,
    )
    book.connection.execute(
        "INSERT INTO crop_year_close (crop_year, closed_on, bale_weight, rate, note)"
        " VALUES (?, ?, ?, ?, ?)",
        (crop_year, on.isoformat(), closing.bale_weight, str(closing.rate), note),
    )

    posted = []
    for producer, carry in sorted(book.allocations.carries(crop_year).items()):
        if carry == 0:
            continue
        amount = closing.value_of(carry)
        if amount == 0:
            continue
        posted.append(
            book.accounts.post(
                Entry(
                    producer=producer,
                    crop_year=crop_year,
                    made=on,
                    kind=EntryKind.ADJUSTMENT,
                    amount=amount,
                    note=f"{carry} of a bale carried at close",
                )
            )
        )
        book.allocations.set_carry(producer, crop_year, Decimal("0"))
    return closing, tuple(posted)


def require_closing(book: Book, crop_year: int) -> Closing:
    """The record of a crop year's close. Raises if it is still open."""
    found = closing_for(book, crop_year)
    if found is None:
        raise NotFoundError("crop year close", str(crop_year))
    return found


def summary(book: Book, crop_year: int) -> tuple[str, ...]:
    """What closing a crop year did, or what is stopping it."""
    found = closing_for(book, crop_year)
    if found is not None:
        return (found.line,)
    reasons = unfinished(book, crop_year)
    if reasons:
        return tuple(f"not ready: {reason}" for reason in reasons)
    carries = {
        producer: carry
        for producer, carry in book.allocations.carries(crop_year).items()
        if carry != 0
    }
    lines = [f"crop year {crop_year} is ready to close"]
    rate = mean_rate(book, crop_year)
    season = totals(book, crop_year)
    for producer, carry in sorted(carries.items()):
        pounds = (Decimal(season.lint_per_bale) * carry).quantize(Decimal("1"))
        lines.append(
            f"  {producer} carries {carry} of a bale, "
            f"{format_money(at_rate(abs(int(pounds)), rate))}"
        )
    return tuple(lines)
