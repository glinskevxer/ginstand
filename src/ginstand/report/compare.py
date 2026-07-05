"""Two crop years beside each other.

Everything in this report exists somewhere else. What it adds is the column of
differences, which is the only column anybody reads, and the rule that a figure
with nothing to compare it against is left blank rather than shown as a change
from zero. A gin that classed nothing last year did not get worse, it has no
comparison, and printing minus a hundred percent is a lie with a number on it.

The rows are the figures a gin manager would actually put side by side. There
are eight of them and there is no way to add a ninth without editing this file,
which is the point: a comparison that can show anything shows nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ginstand.errors import GinstandError
from ginstand.ginning.downtime import season_minutes
from ginstand.ginning.season import totals
from ginstand.report.plastic import season as plastic_season
from ginstand.report.quality import averages
from ginstand.report.table import Align, Column, Table
from ginstand.settle.close import mean_rate
from ginstand.store.book import Book


@dataclass(frozen=True, slots=True)
class Row:
    """One figure, for two crop years, with the change between them."""

    label: str
    earlier: str
    later: str
    change: str

    @property
    def comparable(self) -> bool:
        """Whether there is a change to show."""
        return bool(self.change)


def _number(value: object) -> str:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _change(earlier: Decimal | int | None, later: Decimal | int | None) -> str:
    if earlier is None or later is None:
        return ""
    if isinstance(earlier, int) and isinstance(later, int):
        return f"{later - earlier:+,}"
    return f"{Decimal(later) - Decimal(earlier):+}"


def _figures(book: Book, crop_year: int) -> dict[str, Decimal | int | None]:
    """Every figure for one crop year, with None where there is nothing."""
    found: dict[str, Decimal | int | None] = {
        "bales": None,
        "seed cotton": None,
        "lint turnout": None,
        "staple": None,
        "micronaire": None,
        "loan rate": None,
        "minutes stopped": None,
        "plastic runs": None,
    }
    try:
        season = totals(book, crop_year)
    except GinstandError:
        return found
    found["bales"] = season.bales
    found["seed cotton"] = season.seed_cotton_pounds
    if season.seed_cotton_pounds:
        found["lint turnout"] = season.lint_turnout
    try:
        quality = averages(book, crop_year)
    except GinstandError:
        quality = None
    if quality is not None:
        found["staple"] = quality.staple
        found["micronaire"] = quality.micronaire
        rate = mean_rate(book, crop_year)
        found["loan rate"] = rate if rate else None
    stopped = sum(season_minutes(book, crop_year).values())
    found["minutes stopped"] = stopped if stopped else None
    found["plastic runs"] = len(plastic_season(book, crop_year)) or None
    return found


def rows(book: Book, earlier: int, later: int) -> tuple[Row, ...]:
    """Every figure for two crop years, with the change where there is one."""
    left = _figures(book, earlier)
    right = _figures(book, later)
    return tuple(
        Row(
            label=label,
            earlier="" if left[label] is None else _number(left[label]),
            later="" if right[label] is None else _number(right[label]),
            change=_change(left[label], right[label]),
        )
        for label in left
    )


def compare(book: Book, earlier: int, later: int) -> Table:
    """Two crop years beside each other, with the change between them."""
    return Table(
        title=f"Crop year {earlier} against {later}",
        columns=(
            Column("figure"),
            Column(str(earlier), Align.RIGHT),
            Column(str(later), Align.RIGHT),
            Column("change", Align.RIGHT),
        ),
        rows=tuple(
            (row.label, row.earlier, row.later, row.change) for row in rows(book, earlier, later)
        ),
        empty_note="there is nothing to compare",
    )
