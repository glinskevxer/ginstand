"""How the rechecks went.

A gin that asks for a lot of rechecks and gets the same card back most of the
time is a gin whose own reading is drifting, and the way to find that out is to
count. So the report is a rate rather than a list: how many were asked for, how
many the office moved, and how long it took.

The rate is worth reading by reason as well as overall. A gin can be right about
colour and wrong about micronaire, and one number over both hides it.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from ginstand.model.recheck import Recheck, RecheckOutcome, RecheckReason
from ginstand.report.table import Align, Column, Table
from ginstand.store.book import Book


@dataclass(frozen=True, slots=True)
class Rate:
    """How a set of requests turned out."""

    asked: int
    changed: int
    unchanged: int
    refused: int
    still_out: int

    @property
    def answered(self) -> int:
        """How many the office has come back on."""
        return self.changed + self.unchanged + self.refused

    @property
    def success(self) -> Decimal:
        """The share of answered requests the office moved, to two places."""
        read = self.changed + self.unchanged
        if read == 0:
            return Decimal("0.00")
        return (Decimal(self.changed) * 100 / read).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def line(self) -> str:
        """The line the report prints."""
        return (
            f"{self.asked} asked, {self.changed} changed, {self.unchanged} unchanged, "
            f"{self.refused} refused, {self.still_out} out  ({self.success}%)"
        )


def _rate(requests: tuple[Recheck, ...]) -> Rate:
    counts: Counter[RecheckOutcome] = Counter(item.outcome for item in requests)
    return Rate(
        asked=len(requests),
        changed=counts[RecheckOutcome.CHANGED],
        unchanged=counts[RecheckOutcome.UNCHANGED],
        refused=counts[RecheckOutcome.REFUSED],
        still_out=counts[RecheckOutcome.OPEN],
    )


def _all_requests(book: Book) -> tuple[Recheck, ...]:
    rows = book.connection.execute("SELECT tag FROM recheck ORDER BY requested, id").fetchall()
    seen: list[Recheck] = []
    for row in rows:
        seen.extend(book.rechecks.history_for(str(row["tag"])))
    unique = {item.recheck_id: item for item in seen}
    return tuple(unique[key] for key in sorted(unique))


def overall(book: Book) -> Rate:
    """How every request the gin has ever made turned out."""
    return _rate(_all_requests(book))


def by_reason(book: Book) -> dict[RecheckReason, Rate]:
    """How the requests turned out, split by what the gin queried."""
    requests = _all_requests(book)
    return {
        reason: _rate(tuple(item for item in requests if item.reason is reason))
        for reason in RecheckReason
        if any(item.reason is reason for item in requests)
    }


def rate_table(book: Book) -> Table:
    """The recheck rate, overall and by reason."""
    split = by_reason(book)
    rows = tuple(
        (
            str(reason),
            str(rate.asked),
            str(rate.changed),
            str(rate.unchanged),
            str(rate.refused),
            str(rate.still_out),
            f"{rate.success}%",
        )
        for reason, rate in split.items()
    )
    total = overall(book)
    return Table(
        title="Recheck outcomes",
        columns=(
            Column("reason"),
            Column("asked", Align.RIGHT),
            Column("changed", Align.RIGHT),
            Column("unchanged", Align.RIGHT),
            Column("refused", Align.RIGHT),
            Column("out", Align.RIGHT),
            Column("moved", Align.RIGHT),
        ),
        rows=rows,
        footers=(
            (
                "",
                str(total.asked),
                str(total.changed),
                str(total.unchanged),
                str(total.refused),
                str(total.still_out),
                f"{total.success}%",
            ),
        ),
        empty_note="no rechecks have been asked for",
    )


def turnaround(book: Book, on: date) -> Decimal:
    """The mean days the office took on the requests it has answered."""
    answered = [item for item in _all_requests(book) if not item.open]
    if not answered:
        return Decimal("0.0")
    total = sum(item.days_out(on) for item in answered)
    return (Decimal(total) / len(answered)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
