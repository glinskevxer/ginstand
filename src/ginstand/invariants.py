"""The laws this package's arithmetic obeys, written down once.

Four things have to be true of every number in here, and all four of them are
about money or cotton going missing between one calculation and the next. They
are stated as functions rather than only as tests, for two reasons.

The first is that a law is a property of the package and not of a test file, and
somebody reading ``split_bales`` should be able to find the sentence that says
its output sums to its input without going looking in the suite.

The second is that they can then be run over a range rather than over the three
values a test happened to pick. ``failures`` walks every law across a spread of
awkward inputs and says which one broke and on what, and the command line can
run it against a book that is behaving oddly.

Nothing here is clever. Each law is one line of arithmetic and the value is in
having written it down.
"""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal

from ginstand.ginning.shares import split_bales
from ginstand.model.producer import Lease, LeaseKind
from ginstand.settle.share import split_settlement
from ginstand.units.apportion import apportion
from ginstand.units.moisture import dry_weight, weight_at
from ginstand.units.money import Money


def apportionment_adds_back(total: int, weights: tuple[int, ...]) -> bool:
    """Splitting whole units in proportion never loses or invents one."""
    return sum(apportion(total, list(weights))) == total


def bale_split_adds_back(bales: int, weights: tuple[int, ...]) -> bool:
    """Every bale off a run goes to somebody."""
    producers = {f"P-{index}": weight for index, weight in enumerate(weights)}
    split = split_bales(bales, producers)
    return sum(share.bales for share in split.shares) == bales


CARRY_PLACES = Decimal("0.000001")
"""What one entitlement is rounded to. The carries cancel to within this."""


def carries_cancel(bales: int, weights: tuple[int, ...]) -> bool:
    """What one producer is owed, another has been given.

    So the carries off a single run sum to zero. Almost. An entitlement is
    quantised to six places, and seven bales over three equal producers is
    2.333333 each, which is 6.999999 rather than 7. The millionth left over is
    the quantisation and not a lost bale, so the law is stated with that bound
    on it rather than as an exact zero.

    Writing it as an exact zero is what this function did first, and it was
    false on eleven of the inputs below.
    """
    producers = {f"P-{index}": weight for index, weight in enumerate(weights)}
    split = split_bales(bales, producers)
    total = sum((share.carried_out for share in split.shares), Decimal("0"))
    return abs(total) <= CARRY_PLACES * len(producers)


def lease_split_adds_back(amount: int, share: str) -> bool:
    """A settlement divided under a lease adds back to the settlement."""
    lease = Lease(
        ref="L-1",
        tenant="P-1",
        kind=LeaseKind.SHARE,
        landlord="P-2",
        landlord_share=Decimal(share),
    )
    split = split_settlement(Money(amount), lease)
    return split.tenant_amount + split.landlord_amount == amount


def moisture_round_trips(pounds: int, moisture: str) -> bool:
    """Drying cotton and putting the water back lands within a pound."""
    reading = Decimal(moisture)
    return abs(weight_at(dry_weight(pounds, reading), reading) - pounds) <= 1


WEIGHTS: tuple[tuple[int, ...], ...] = (
    (1, 1),
    (1, 1, 1),
    (3, 1),
    (122_400, 88_150, 46_900, 15_320),
    (1, 999_999),
    (7, 7, 7, 7, 7, 7, 7),
    (33, 33, 34),
    (5_000, 0, 5_000),
)
"""Weight splits that have caught a rounding mistake somewhere."""

COUNTS: tuple[int, ...] = (0, 1, 2, 3, 7, 13, 61, 100, 999)
"""Unit counts to split, including the ones that divide badly."""

AMOUNTS: tuple[int, ...] = (0, 1, 3, 7, 100, 10_001, 123_457, -1, -7, -100_003)
"""Amounts in cents, including the negatives a producer owes."""

SHARES: tuple[str, ...] = ("0.25", "0.3333", "0.5", "0.6667", "0.01", "0.99")
"""Landlord shares, including the ones that do not divide."""

POUNDS: tuple[int, ...] = (0, 1, 480, 490, 512, 1_000, 22_060, 60_000)
READINGS: tuple[str, ...] = ("0.0", "5.0", "6.8", "9.4", "11.0", "16.5", "25.0")


def failures() -> Iterator[str]:
    """Every law that does not hold, and the input it broke on."""
    for total in COUNTS:
        for weights in WEIGHTS:
            if not apportionment_adds_back(total, weights):
                yield f"apportionment lost a unit at {total} over {weights}"
            if not bale_split_adds_back(total, weights):
                yield f"a bale went missing at {total} over {weights}"
            if not carries_cancel(total, weights):
                yield f"the carries do not cancel at {total} over {weights}"
    for amount in AMOUNTS:
        for share in SHARES:
            if not lease_split_adds_back(amount, share):
                yield f"a lease split lost a cent at {amount} on {share}"
    for pounds in POUNDS:
        for reading in READINGS:
            if not moisture_round_trips(pounds, reading):
                yield f"moisture did not round trip at {pounds} lb, {reading}%"


def holds() -> bool:
    """Whether every law holds across every input the package checks."""
    return not any(failures())
