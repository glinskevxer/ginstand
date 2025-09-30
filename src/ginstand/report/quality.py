"""What a crop year classed like.

This is the report a gin manager takes to a growers' meeting, so the numbers in
it get argued about in public and every one of them has to be defensible.

Averages are weighted by bale weight throughout. A mean micronaire over bales
rather than over pounds is a different number, and the difference is largest in
exactly the season where somebody asks: one where a few light bales classed
badly.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ginstand.classing.matter import ExtraneousKind
from ginstand.classing.standing import OffSchedule, standing_of
from ginstand.errors import StateError
from ginstand.report.table import Align, Column, Table
from ginstand.store.book import Book


@dataclass(frozen=True, slots=True)
class Averages:
    """The weighted means for a set of classed bales."""

    bales: int
    pounds: int
    micronaire: Decimal
    strength: Decimal
    uniformity: Decimal
    staple: Decimal
    leaf: Decimal


def _cards_for(book: Book, crop_year: int) -> tuple[tuple[str, int], ...]:
    found = []
    for card in book.cards.list_all():
        bale = book.bales.get(card.tag)
        if bale.crop_year == crop_year:
            found.append((card.tag, bale.net_pounds))
    return tuple(found)


def averages(book: Book, crop_year: int) -> Averages:
    """The weighted means across every classed bale of a crop year."""
    cards = _cards_for(book, crop_year)
    if not cards:
        raise StateError(f"no bale in crop year {crop_year} has been classed")
    pounds = sum(weight for _, weight in cards)
    totals = {
        "mic": Decimal(0),
        "str": Decimal(0),
        "uni": Decimal(0),
        "sta": Decimal(0),
        "leaf": Decimal(0),
    }
    for tag, weight in cards:
        card = book.cards.get(tag)
        totals["mic"] += card.micronaire * weight
        totals["str"] += card.strength * weight
        totals["uni"] += card.uniformity * weight
        totals["sta"] += Decimal(card.staple) * weight
        totals["leaf"] += Decimal(card.leaf) * weight
    places = Decimal("0.01")
    basis = Decimal(pounds)
    return Averages(
        bales=len(cards),
        pounds=pounds,
        micronaire=(totals["mic"] / basis).quantize(places, rounding=ROUND_HALF_UP),
        strength=(totals["str"] / basis).quantize(places, rounding=ROUND_HALF_UP),
        uniformity=(totals["uni"] / basis).quantize(places, rounding=ROUND_HALF_UP),
        staple=(totals["sta"] / basis).quantize(places, rounding=ROUND_HALF_UP),
        leaf=(totals["leaf"] / basis).quantize(places, rounding=ROUND_HALF_UP),
    )


def colour_spread(book: Book, crop_year: int) -> Table:
    """How the crop year's bales fell across the colour chart."""
    counts: Counter[int] = Counter()
    for tag, _ in _cards_for(book, crop_year):
        counts[book.cards.get(tag).color.code] += 1
    total = sum(counts.values())
    rows = [
        (
            str(code),
            book.cards.get(
                next(
                    t
                    for t, _ in _cards_for(book, crop_year)
                    if book.cards.get(t).color.code == code
                )
            ).color.name,
            str(count),
            f"{(Decimal(count) * 100 / total).quantize(Decimal('0.1'))}%",
        )
        for code, count in sorted(counts.items())
    ]
    return Table(
        title=f"Colour grades, crop year {crop_year}",
        columns=(
            Column("code"),
            Column("grade"),
            Column("bales", Align.RIGHT),
            Column("share", Align.RIGHT),
        ),
        rows=tuple(rows),
        footers=(("", "", str(total), "100.0%"),) if rows else (),
        empty_note="nothing has been classed",
    )


def staple_spread(book: Book, crop_year: int) -> Table:
    """How the crop year's bales fell across staple length."""
    counts: Counter[int] = Counter()
    for tag, _ in _cards_for(book, crop_year):
        counts[book.cards.get(tag).staple] += 1
    total = sum(counts.values())
    rows = [
        (
            str(staple),
            str(count),
            f"{(Decimal(count) * 100 / total).quantize(Decimal('0.1'))}%",
        )
        for staple, count in sorted(counts.items())
    ]
    return Table(
        title=f"Staple, crop year {crop_year}",
        columns=(Column("staple"), Column("bales", Align.RIGHT), Column("share", Align.RIGHT)),
        rows=tuple(rows),
        footers=(("", str(total), "100.0%"),) if rows else (),
        empty_note="nothing has been classed",
    )


def off_schedule(book: Book, crop_year: int) -> Table:
    """Every bale off the schedule, and which rule put it there."""
    rows = []
    for tag, weight in _cards_for(book, crop_year):
        standing = standing_of(book.cards.get(tag))
        if standing.on_schedule:
            continue
        rows.append(
            (
                tag,
                str(weight),
                ", ".join(str(reason) for reason in standing.reasons),
                "ours" if standing.arguable else "the office",
            )
        )
    return Table(
        title=f"Bales off the schedule, crop year {crop_year}",
        columns=(
            Column("tag"),
            Column("net", Align.RIGHT),
            Column("reason"),
            Column("whose rule"),
        ),
        rows=tuple(rows),
        empty_note="every classed bale is on the schedule",
    )


def contamination(book: Book, crop_year: int) -> Table:
    """Extraneous matter notes across the crop year, worst first."""
    counts: Counter[str] = Counter()
    for tag, _ in _cards_for(book, crop_year):
        for note in book.cards.get(tag).extraneous:
            counts[note.code] += 1
    rows = [(code, str(count)) for code, count in sorted(counts.items())]
    plastic = sum(
        count
        for code, count in counts.items()
        if code.startswith(ExtraneousKind.PLASTIC.name[:2].upper())
    )
    return Table(
        title=f"Extraneous matter, crop year {crop_year}",
        columns=(Column("code"), Column("bales", Align.RIGHT)),
        rows=tuple(rows),
        footers=(("plastic", str(plastic)),) if rows else (),
        empty_note="no extraneous matter was noted",
    )


def summary(book: Book, crop_year: int) -> tuple[str, ...]:
    """The averages, as the lines that head the quality report."""
    figures = averages(book, crop_year)
    off = [
        reason
        for tag, _ in _cards_for(book, crop_year)
        for reason in standing_of(book.cards.get(tag)).reasons
    ]
    counted = Counter(off)
    lines = [
        f"Crop year {crop_year}: {figures.bales} bales classed, {figures.pounds:,} lb",
        f"  mic {figures.micronaire}  staple {figures.staple}  "
        f"strength {figures.strength}  uniformity {figures.uniformity}  "
        f"leaf {figures.leaf}",
    ]
    if counted:
        parts = ", ".join(
            f"{counted[reason]} {reason}" for reason in OffSchedule if counted[reason]
        )
        lines.append(f"  off the schedule: {parts}")
    return tuple(lines)
