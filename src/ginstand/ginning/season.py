"""What a crop year came to, added up.

These are the totals every report of a season works off, and they are a rule
rather than a report: closing a crop year needs the mean bale weight, and a
report is the wrong place for a settlement to go looking for it.

The turnout here is worked out over the whole season rather than averaged over
the runs. Averaging run turnouts weights a fifty bale run the same as a five
hundred bale one, and the answer comes out about a point high in a season with a
slow start.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ginstand.errors import StateError
from ginstand.ginning.seed import seed_pounds
from ginstand.store.book import Book
from ginstand.units.apportion import proportion


@dataclass(frozen=True, slots=True)
class Season:
    """A crop year's totals."""

    crop_year: int
    runs: int
    open_runs: int
    modules: int
    seed_cotton_pounds: int
    bales: int
    lint_pounds: int
    seed_cotton_seed_pounds: int

    @property
    def lint_turnout(self) -> Decimal:
        """Lint over seed cotton across the whole season."""
        return proportion(self.lint_pounds, self.seed_cotton_pounds)

    @property
    def seed_turnout(self) -> Decimal:
        """Seed over seed cotton across the whole season."""
        return proportion(self.seed_cotton_seed_pounds, self.seed_cotton_pounds)

    @property
    def lint_per_bale(self) -> int:
        """Mean net lint per bale over the season."""
        if self.bales == 0:
            raise StateError(f"crop year {self.crop_year} has no bales")
        return round(self.lint_pounds / self.bales)


def totals(book: Book, crop_year: int) -> Season:
    """Add a crop year up."""
    runs = book.runs.for_crop_year(crop_year)
    if not runs:
        raise StateError(f"crop year {crop_year} has no gin runs")
    modules = 0
    seed_cotton = 0
    bales = 0
    lint = 0
    seed = 0
    for run in runs:
        modules += len(book.runs.modules_in(run.ref))
        seed_cotton += book.runs.seed_cotton_in(run.ref)
        bales += book.bales.count_for_run(run.ref)
        lint += book.bales.lint_pounds_for_run(run.ref)
        seed += seed_pounds(book, run.ref)
    return Season(
        crop_year=crop_year,
        runs=len(runs),
        open_runs=sum(1 for run in runs if run.is_open),
        modules=modules,
        seed_cotton_pounds=seed_cotton,
        bales=bales,
        lint_pounds=lint,
        seed_cotton_seed_pounds=seed,
    )
