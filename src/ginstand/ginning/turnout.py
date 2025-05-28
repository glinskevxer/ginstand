"""Turnout: how much lint came out of the seed cotton that went in.

Turnout is the number a gin is judged on and the number a producer argues about,
and it is only meaningful once the run is closed. A figure taken part way
through a run is the ratio of the lint pressed so far to all the seed cotton fed
so far, and those two are never in step: the seed cotton is in the machine
before the bale comes off the end of it.

Both are offered here, and they are different functions with different names.
Nothing decides which one the caller meant, because that decision has been got
wrong in enough gin offices to be worth two names.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from ginstand.errors import StateError
from ginstand.store.book import Book
from ginstand.units.apportion import proportion

LOW_TURNOUT = Decimal("0.2800")
"""Below this the run either had wet cotton or a stand set badly."""

HIGH_TURNOUT = Decimal("0.4500")
"""Above this the seed cotton weight is wrong, not the lint."""


@dataclass(frozen=True, slots=True)
class Turnout:
    """What a run turned out, and the numbers it was worked out from."""

    run: str
    seed_cotton_pounds: int
    lint_pounds: int
    bales: int
    final: bool

    @property
    def lint_turnout(self) -> Decimal:
        """Lint divided by seed cotton, to four places."""
        return proportion(self.lint_pounds, self.seed_cotton_pounds)

    @property
    def lint_per_bale(self) -> int:
        """Mean net lint per bale, rounded to the pound."""
        if self.bales == 0:
            raise StateError(f"gin run {self.run} has pressed no bales")
        return round(self.lint_pounds / self.bales)

    @property
    def seed_cotton_per_bale(self) -> int:
        """How much seed cotton it took to make a bale on this run."""
        if self.bales == 0:
            raise StateError(f"gin run {self.run} has pressed no bales")
        return round(self.seed_cotton_pounds / self.bales)

    @property
    def low(self) -> bool:
        """Whether the turnout is below the band a run should land in."""
        return self.lint_turnout < LOW_TURNOUT

    @property
    def high(self) -> bool:
        """Whether the turnout is above the band, which points at the scale."""
        return self.lint_turnout > HIGH_TURNOUT

    @property
    def in_band(self) -> bool:
        """Whether the turnout is one the gin manager would not query."""
        return not self.low and not self.high

    @property
    def line(self) -> str:
        """The one line that goes on the run sheet."""
        state = "final" if self.final else "so far"
        flag = "" if self.in_band else ("  LOW" if self.low else "  HIGH")
        return f"{self.run}  {self.bales} bales  {self.lint_turnout} turnout ({state}){flag}"


def _turnout(book: Book, run_ref: str, final: bool) -> Turnout:
    run = book.runs.get(run_ref)
    seed_cotton = book.runs.seed_cotton_in(run.ref)
    if seed_cotton == 0:
        raise StateError(f"gin run {run.ref} has no seed cotton in it, so it has no turnout")
    return Turnout(
        run=run.ref,
        seed_cotton_pounds=seed_cotton,
        lint_pounds=book.bales.lint_pounds_for_run(run.ref),
        bales=book.bales.count_for_run(run.ref),
        final=final,
    )


def turnout_for(book: Book, run_ref: str) -> Turnout:
    """The run's final turnout. Refuses a run that is still open."""
    run = book.runs.get(run_ref)
    if run.is_open:
        raise StateError(f"gin run {run.ref} is still open, so its turnout is not final yet")
    return _turnout(book, run.ref, final=True)


def turnout_so_far(book: Book, run_ref: str) -> Turnout:
    """The run's turnout as things stand, which is not the same number."""
    return _turnout(book, run_ref, final=False)
