"""The producer statement: lint, seed, charges, and who it gets split with.

The order is fixed and it is the order a producer reads. Lint value first,
because it is the number they came for. Seed credit next, because on a poor lot
it is what keeps the statement positive. Charges after that, because they are
what the gin is owed. Then the split, on the total, once.

A statement can be issued before every bale is classed, and it says so. Waiting
for the last card would hold up the whole run's money for one sample, so the
unclassed bales are listed and left out of the lint value, and the statement is
marked provisional. A provisional statement is not a wrong statement, it is an
incomplete one, and the difference is written on its face.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from ginstand.charges.tariff import Bill, Tariff, bill
from ginstand.ginning.seed import seed_by_producer
from ginstand.loan.lot import LotValue, value_lot
from ginstand.loan.schedule import schedule_for
from ginstand.settle.gather import RunShare, gather, gather_all
from ginstand.settle.share import LeaseSplit, split_settlement
from ginstand.store.book import Book
from ginstand.units.apportion import apportion
from ginstand.units.money import Money, format_money

POUNDS_PER_TON = 2000


@dataclass(frozen=True, slots=True)
class Statement:
    """What one producer is paid for one run."""

    share: RunShare
    issued: date
    lint: LotValue | None
    seed_pounds: int
    seed_credit: Money
    charges: Bill
    splits: tuple[LeaseSplit, ...]

    @property
    def lint_value(self) -> Money:
        """What the classed bales came to."""
        return Money(0) if self.lint is None else self.lint.value

    @property
    def gross(self) -> Money:
        """Lint value plus the seed credit."""
        return Money(self.lint_value + self.seed_credit)

    @property
    def total(self) -> Money:
        """What is left after the gin's charges. Negative means the producer owes."""
        return Money(self.gross - self.charges.total)

    @property
    def provisional(self) -> bool:
        """Whether bales are still waiting on a card."""
        return not self.share.complete

    @property
    def lines(self) -> tuple[str, ...]:
        """The statement as printed lines."""
        rows = [
            f"Gin run {self.share.run}   {self.share.producer}   issued {self.issued.isoformat()}",
            f"  {self.share.modules} modules, {self.share.seed_cotton_pounds:,} lb "
            f"seed cotton, {self.share.bales} bales",
            f"  lint            {format_money(self.lint_value):>12}",
            f"  seed credit     {format_money(self.seed_credit):>12}",
            f"  charges         {format_money(Money(-self.charges.total)):>12}",
            f"  total           {format_money(self.total):>12}",
        ]
        if self.provisional:
            rows.append(f"  PROVISIONAL: {len(self.share.unclassed)} bales not classed")
        for split in self.splits:
            rows.append(f"  lease {split.lease}")
            rows.extend(f"    {line}" for line in split.lines)
        return tuple(rows)


def _spread(total: Money, weights: dict[str, int]) -> dict[str, Money]:
    """Divide an amount between leases in proportion to their seed cotton."""
    keys = list(weights)
    shares = apportion(abs(total), [weights[key] for key in keys])
    sign = -1 if total < 0 else 1
    return {key: Money(sign * amount) for key, amount in zip(keys, shares, strict=True)}


def seed_credit_for(pounds: int, price_per_ton: Money) -> Money:
    """What a producer's seed is worth at a price per ton."""
    tons = Decimal(pounds) / POUNDS_PER_TON
    return Money(
        int((tons * Decimal(price_per_ton)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    )


def settle(
    book: Book,
    run_ref: str,
    producer: str,
    tariff: Tariff,
    seed_price_per_ton: Money,
    on: date,
    extras: tuple[str, ...] = (),
) -> Statement:
    """Work out one producer's statement for one run."""
    share = gather(book, run_ref, producer)
    schedule = schedule_for(share.crop_year)
    enrolled = book.producers.get(share.producer).enrolled_for_loan

    lint = None
    if share.classed:
        lint = value_lot(
            schedule,
            [(book.cards.get(tag), book.bales.get(tag).net_pounds) for tag in share.classed],
            enrolled,
        )

    weights = {other.producer: other.seed_cotton_pounds for other in gather_all(book, run_ref)}
    seed_pounds = seed_by_producer(book, run_ref, weights)[share.producer]
    credit = seed_credit_for(seed_pounds, seed_price_per_ton)

    charges = bill(
        tariff,
        bales=share.bales,
        seed_cotton_pounds=share.seed_cotton_pounds,
        modules=share.modules,
        extras=extras,
    )

    statement = Statement(
        share=share,
        issued=on,
        lint=lint,
        seed_pounds=seed_pounds,
        seed_credit=credit,
        charges=charges,
        splits=(),
    )
    spread = _spread(statement.total, share.lease_pounds)
    splits = tuple(
        split_settlement(spread[lease], book.leases.get(lease)) for lease in share.leases
    )
    return Statement(
        share=share,
        issued=on,
        lint=lint,
        seed_pounds=seed_pounds,
        seed_credit=credit,
        charges=charges,
        splits=splits,
    )
