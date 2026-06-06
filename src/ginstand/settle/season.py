"""A producer's whole season on one page.

Every other report in this package is organised around a run, because that is
how the gin works. A producer is not organised around a run: they ginned four
times between October and January and what they want is one page that adds up.

So this walks their runs and totals them, and puts the account beside the
totals. The two halves are worth reading together and they answer different
questions. The left half is what they grew. The right half is what they have
been paid, which is a different number and, in a season with a late run still
provisional, a smaller one.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ginstand.errors import StateError
from ginstand.model.account import EntryKind
from ginstand.settle.gather import RunShare, gather, producers_in
from ginstand.store.book import Book
from ginstand.units.apportion import proportion
from ginstand.units.money import Money, format_money


@dataclass(frozen=True, slots=True)
class ProducerSeason:
    """One producer's crop year."""

    producer: str
    name: str
    crop_year: int
    shares: tuple[RunShare, ...]
    settled: Money
    adjusted: Money
    paid: Money

    @property
    def runs(self) -> int:
        """How many runs they were on."""
        return len(self.shares)

    @property
    def modules(self) -> int:
        """How many modules they put over the scale."""
        return sum(share.modules for share in self.shares)

    @property
    def seed_cotton_pounds(self) -> int:
        """Every pound of seed cotton they ginned."""
        return sum(share.seed_cotton_pounds for share in self.shares)

    @property
    def bales(self) -> int:
        """How many bales came back to them."""
        return sum(share.bales for share in self.shares)

    @property
    def lint_pounds(self) -> int:
        """Every pound of lint they own."""
        return sum(share.lint_pounds for share in self.shares)

    @property
    def unclassed(self) -> int:
        """How many of their bales are still waiting on a card."""
        return sum(len(share.unclassed) for share in self.shares)

    @property
    def turnout(self) -> Decimal:
        """Lint over seed cotton across their whole season."""
        if self.seed_cotton_pounds == 0:
            return Decimal("0.0000")
        return proportion(self.lint_pounds, self.seed_cotton_pounds)

    @property
    def balance(self) -> Money:
        """What the gin still owes them."""
        return Money(self.settled + self.adjusted + self.paid)

    @property
    def unsettled_runs(self) -> tuple[str, ...]:
        """Every run of theirs that has not been agreed onto the account."""
        return tuple(share.run for share in self.shares if share.unclassed)

    @property
    def lines(self) -> tuple[str, ...]:
        """The page, as printed lines."""
        rows = [
            f"{self.producer}  {self.name}  crop year {self.crop_year}",
            "",
            f"  {self.runs} runs, {self.modules} modules, "
            f"{self.seed_cotton_pounds:,} lb seed cotton",
            f"  {self.bales} bales, {self.lint_pounds:,} lb lint, turnout {self.turnout}",
            "",
            f"  settlements  {format_money(self.settled):>12}",
            f"  adjustments  {format_money(self.adjusted):>12}",
            f"  payments     {format_money(self.paid):>12}",
            f"  balance      {format_money(self.balance):>12}",
        ]
        if self.unclassed:
            rows.append("")
            rows.append(
                f"  {self.unclassed} bales are still waiting on a card, on "
                f"{', '.join(self.unsettled_runs)}"
            )
        return tuple(rows)


def for_producer(book: Book, producer: str, crop_year: int) -> ProducerSeason:
    """One producer's crop year, gathered and totalled."""
    who = book.producers.get(producer)
    shares = []
    for run in book.runs.for_crop_year(crop_year):
        if run.is_open or not book.allocations.run_is_allocated(run.ref):
            continue
        if who.ref in producers_in(book, run.ref):
            shares.append(gather(book, run.ref, who.ref))
    if not shares:
        raise StateError(f"producer {who.ref} has no settled run in crop year {crop_year}")
    totals = book.accounts.totals(who.ref, crop_year)
    return ProducerSeason(
        producer=who.ref,
        name=who.name,
        crop_year=crop_year,
        shares=tuple(shares),
        settled=totals[EntryKind.SETTLEMENT],
        adjusted=totals[EntryKind.ADJUSTMENT],
        paid=totals[EntryKind.PAYMENT],
    )
