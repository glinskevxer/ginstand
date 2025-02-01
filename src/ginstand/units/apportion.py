"""Splitting a whole thing between claimants in proportion to their weight.

A gin run mixes modules from several producers and presses whole bales. The
bales have to go back to the producers in proportion to the seed cotton each of
them put in, and a bale cannot be cut in half. That is this module.

The method is largest remainder. Give everyone their whole part, then hand the
leftover units out one at a time to whoever has the largest fraction still
owed. It is the only method here because it is the one that a producer can be
walked through on the phone: the arithmetic is theirs to check.

Ties go to the earlier claimant. That is arbitrary, and it is written down and
tested so it is at least the same arbitrary thing every time.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from ginstand.errors import ValidationError


def apportion(total: int, weights: Sequence[int]) -> list[int]:
    """Split ``total`` whole units between claimants, in proportion to ``weights``.

    The result always sums to ``total`` exactly. That is the property worth
    having: every other rounding scheme leaves a unit unaccounted for somewhere
    and the gin office finds it a month later.
    """
    if total < 0:
        raise ValidationError("total", "must not be negative")
    if not weights:
        raise ValidationError("weights", "there is nobody to split between")
    for index, weight in enumerate(weights):
        if weight < 0:
            raise ValidationError(f"weights[{index}]", "must not be negative")
    basis = sum(weights)
    if basis == 0:
        raise ValidationError("weights", "are all zero, so there is nothing to split on")

    shares = []
    for weight in weights:
        exact = Decimal(total) * Decimal(weight) / Decimal(basis)
        whole = int(exact)
        shares.append((whole, exact - whole))
    handed_out = sum(whole for whole, _ in shares)
    leftover = total - handed_out

    order = sorted(range(len(shares)), key=lambda i: (-shares[i][1], i))
    result = [whole for whole, _ in shares]
    for position in range(leftover):
        result[order[position % len(order)]] += 1
    return result


def largest_remainder_order(weights: Sequence[int], total: int) -> list[int]:
    """The order claimants stand in to receive a leftover unit.

    Exposed so a settlement statement can print why one producer got the odd
    bale and the next one did not.
    """
    if not weights:
        raise ValidationError("weights", "there is nobody to split between")
    basis = sum(weights)
    if basis == 0:
        raise ValidationError("weights", "are all zero, so there is nothing to split on")
    fractions = []
    for weight in weights:
        exact = Decimal(total) * Decimal(weight) / Decimal(basis)
        fractions.append(exact - int(exact))
    return sorted(range(len(weights)), key=lambda i: (-fractions[i], i))


def proportion(part: int, whole: int, places: str = "0.0001") -> Decimal:
    """``part`` as a fraction of ``whole``, to the places given.

    Used for turnout and for a producer's share of a run. Zero over zero is a
    refusal rather than a zero, because a run with no seed cotton in it has no
    turnout and printing 0.0000 would say it had a bad one.
    """
    if whole == 0:
        raise ValidationError("basis", "is zero, so there is no proportion to take")
    if whole < 0 or part < 0:
        raise ValidationError("proportion", "must not be negative")
    return (Decimal(part) / Decimal(whole)).quantize(Decimal(places))
