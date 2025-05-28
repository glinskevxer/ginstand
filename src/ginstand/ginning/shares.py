"""Working out how many bales off a run belong to each producer.

A run mixes cotton from several producers and presses whole bales. Nobody's
seed cotton divides into a whole number of bales, so every run leaves each
producer owed a fraction of one. That fraction is carried to their next run in
the same crop year rather than rounded away, and the carry is added to their
entitlement before the whole bales are handed out.

So the carry decides the allocation and the allocation decides the next carry.
That is the whole of it, and it is why a producer's bale count on one run cannot
be checked without knowing what happened on the run before.

Nothing in here touches the book. It takes weights and carries in and gives a
split back, which is what makes it possible to show a producer the arithmetic.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ginstand.errors import ValidationError

_BALE_PLACES = Decimal("0.000001")


@dataclass(frozen=True, slots=True)
class Share:
    """One producer's part of a run."""

    producer: str
    seed_cotton_pounds: int
    entitlement: Decimal
    carried_in: Decimal
    bales: int
    carried_out: Decimal

    @property
    def claim(self) -> Decimal:
        """What this producer was owed on this run, carry included."""
        return self.entitlement + self.carried_in

    @property
    def line(self) -> str:
        """The line that goes on the run's allocation sheet."""
        return (
            f"{self.producer}  {self.seed_cotton_pounds:,} lb  "
            f"claim {self.claim}  {self.bales} bales  carry {self.carried_out}"
        )


@dataclass(frozen=True, slots=True)
class Split:
    """A whole run divided between the producers who fed it."""

    bales: int
    seed_cotton_pounds: int
    shares: tuple[Share, ...]

    def for_producer(self, producer: str) -> Share:
        """One producer's share of this run."""
        for share in self.shares:
            if share.producer == producer:
                return share
        raise ValidationError("producer", f"{producer} put no cotton into this run")

    @property
    def producers(self) -> tuple[str, ...]:
        """The producers in the run, in the order they were given."""
        return tuple(share.producer for share in self.shares)


def split_bales(
    bales: int,
    weights: Mapping[str, int],
    carry: Mapping[str, Decimal] | None = None,
) -> Split:
    """Divide ``bales`` between producers by seed cotton weight, honouring carries.

    The order of ``weights`` is kept. It decides who gets the odd bale when two
    producers are owed the same fraction, and a run sheet that prints the
    producers in feed order should hand the bale out in feed order too.
    """
    if bales < 0:
        raise ValidationError("bales", "must not be negative")
    if not weights:
        raise ValidationError("weights", "no producer put cotton into this run")
    total = sum(weights.values())
    if total <= 0:
        raise ValidationError("weights", "the run has no seed cotton in it")
    for producer, pounds in weights.items():
        if pounds < 0:
            raise ValidationError(producer, "put a negative weight into the run")

    carried = dict(carry or {})
    claims: list[tuple[str, Decimal, Decimal, Decimal]] = []
    for producer, pounds in weights.items():
        entitlement = (Decimal(bales) * Decimal(pounds) / Decimal(total)).quantize(
            _BALE_PLACES, rounding=ROUND_HALF_UP
        )
        carried_in = carried.get(producer, Decimal("0"))
        claims.append((producer, entitlement, carried_in, entitlement + carried_in))

    whole = {producer: max(0, int(claim)) for producer, _, _, claim in claims}
    handed_out = sum(whole.values())
    leftover = bales - handed_out
    if leftover > 0:
        order = sorted(
            range(len(claims)),
            key=lambda i: (-(claims[i][3] - int(claims[i][3])), i),
        )
        for position in range(leftover):
            whole[claims[order[position % len(order)]][0]] += 1

    shares = tuple(
        Share(
            producer=producer,
            seed_cotton_pounds=weights[producer],
            entitlement=entitlement,
            carried_in=carried_in,
            bales=whole[producer],
            carried_out=claim - whole[producer],
        )
        for producer, entitlement, carried_in, claim in claims
    )
    return Split(bales=bales, seed_cotton_pounds=total, shares=shares)


def carries_from(split: Split) -> dict[str, Decimal]:
    """The carries this split leaves behind, ready for the next run."""
    return {share.producer: share.carried_out for share in split.shares}
