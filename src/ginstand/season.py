"""The crop year, and the date handling that hangs off it.

A cotton crop year runs from the first of August to the thirty first of July.
Ginning starts in September and runs into January, so a single ginning season
straddles two calendar years and everything downstream of it is filed under the
crop year rather than the calendar year: the bale tag, the loan schedule, the
classing office's own numbering.

Nothing in this package reads the wall clock. Every operation that needs to know
what day it is takes the day as an argument. That is what makes a settlement
reproducible a year later, and it is what lets the tests run on any day of the
year without a frozen clock.
"""

from __future__ import annotations

from datetime import date, timedelta

from ginstand.errors import ValidationError

CROP_YEAR_START_MONTH = 8
"""August. The crop year is named for the calendar year its August falls in."""

FIRST_CROP_YEAR = 2000
LAST_CROP_YEAR = 2099


def check_crop_year(year: int, field: str = "crop year") -> int:
    """Return ``year`` if this package can file records under it."""
    if isinstance(year, bool) or not isinstance(year, int):
        raise ValidationError(field, "must be a whole year")
    if year < FIRST_CROP_YEAR or year > LAST_CROP_YEAR:
        raise ValidationError(
            field, f"must be between {FIRST_CROP_YEAR} and {LAST_CROP_YEAR}, got {year}"
        )
    return year


def crop_year_of(day: date) -> int:
    """The crop year a day falls in.

    The thirty first of July belongs to the crop year that started the previous
    August. This is the line that catches people out on a late shipment.
    """
    return day.year if day.month >= CROP_YEAR_START_MONTH else day.year - 1


def crop_year_bounds(year: int) -> tuple[date, date]:
    """The first and last day of a crop year, both inclusive."""
    check_crop_year(year)
    return date(year, CROP_YEAR_START_MONTH, 1), date(
        year + 1, CROP_YEAR_START_MONTH, 1
    ) - timedelta(days=1)


def in_crop_year(day: date, year: int) -> bool:
    """Whether a day falls inside a crop year."""
    check_crop_year(year)
    return crop_year_of(day) == year


def require_in_crop_year(day: date, year: int, field: str = "date") -> date:
    """Return ``day`` if it falls in ``year``, else raise naming both."""
    if not in_crop_year(day, year):
        first, last = crop_year_bounds(year)
        raise ValidationError(
            field, f"{day.isoformat()} is outside crop year {year}, which runs {first} to {last}"
        )
    return day


def season_label(year: int) -> str:
    """A crop year as the office writes it on a folder: 2025/26."""
    check_crop_year(year)
    return f"{year}/{(year + 1) % 100:02d}"


def parse_date(text: str, field: str = "date") -> date:
    """Read a date. ISO only, because every other order is ambiguous somewhere."""
    cleaned = text.strip()
    if not cleaned:
        raise ValidationError(field, "is empty")
    try:
        return date.fromisoformat(cleaned)
    except ValueError:
        raise ValidationError(
            field, f"must be an ISO date such as 2025-09-14, got {text!r}"
        ) from None


def not_before(day: date, earliest: date, field: str = "date") -> date:
    """Return ``day`` if it is on or after ``earliest``, else raise."""
    if day < earliest:
        raise ValidationError(field, f"{day.isoformat()} is before {earliest.isoformat()}")
    return day


def days_between(start: date, end: date) -> int:
    """Whole days from ``start`` to ``end``. Negative if they are the wrong way round."""
    return (end - start).days
