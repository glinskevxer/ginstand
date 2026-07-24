"""Bale weight control, measured at two levels.

A gin is judged on bale weight twice over and they are different judgements.

The run is measured against the press's target. A run whose bales average four
hundred and twenty pounds is making light bales, which costs the producer
nothing and costs the gin a bale's worth of bagging and ties for every twelve it
presses.

A bale is measured against its own run's mean, not against the target. A run of
consistently light bales is under control and somebody should look at the press
settings. One bale forty pounds off the run it came from is a bale that hung up,
and it is worth going to look at now.

That is the composition worth understanding here: the run's mean decides what
each of its bales is measured against, so the same 455 pound bale is unremarkable
on one run and a finding on another.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ginstand.errors import StateError
from ginstand.ginning.season import runs_pressed
from ginstand.model.bale import Bale
from ginstand.store.book import Book

TARGET_POUNDS = 500
"""What the press is set to make."""

RUN_TOLERANCE = 30
"""How far a run's mean may sit from the target before the press is queried."""

BALE_TOLERANCE = 40
"""How far a bale may sit from its own run's mean before it is worth a look."""

MINIMUM_BALES = 5
"""Below this a run's mean is not a mean, so bales are measured on the target."""


@dataclass(frozen=True, slots=True)
class Control:
    """One run's bale weights."""

    run: str
    bales: int
    mean: Decimal
    lightest: int
    heaviest: int
    basis: Decimal
    outliers: tuple[str, ...]

    @property
    def spread(self) -> int:
        """Heaviest less lightest."""
        return self.heaviest - self.lightest

    @property
    def off_target(self) -> Decimal:
        """How far the run's mean sits from the target, signed."""
        return self.mean - TARGET_POUNDS

    @property
    def in_control(self) -> bool:
        """Whether the run's own mean is close enough to the target."""
        return abs(self.off_target) <= RUN_TOLERANCE

    @property
    def clean(self) -> bool:
        """Whether the run is in control and no bale is off its own run."""
        return self.in_control and not self.outliers

    @property
    def line(self) -> str:
        """The line the press report prints."""
        state = "" if self.in_control else "  PRESS"
        flagged = f"  {len(self.outliers)} to look at" if self.outliers else ""
        return (
            f"{self.run}  {self.bales} bales  mean {self.mean}  "
            f"spread {self.spread}{state}{flagged}"
        )


def mean_of(bales: tuple[Bale, ...]) -> Decimal:
    """The mean net weight of some bales, to one place."""
    if not bales:
        raise StateError("there are no bales to take a mean of")
    total = sum(bale.net_pounds for bale in bales)
    return (Decimal(total) / len(bales)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def control_for(book: Book, run_ref: str) -> Control:
    """Work out a run's bale weight control.

    A short run is measured on the target rather than on its own mean, because
    the mean of four bales is mostly the bales. That is the second half of the
    composition: which basis applies depends on how many bales there are.
    """
    run = book.runs.get(run_ref)
    bales = book.bales.for_run(run.ref)
    if not bales:
        raise StateError(f"gin run {run.ref} has pressed no bales")
    mean = mean_of(bales)
    basis = mean if len(bales) >= MINIMUM_BALES else Decimal(TARGET_POUNDS)
    outliers = tuple(
        bale.tag for bale in bales if abs(Decimal(bale.net_pounds) - basis) > BALE_TOLERANCE
    )
    return Control(
        run=run.ref,
        bales=len(bales),
        mean=mean,
        lightest=min(bale.net_pounds for bale in bales),
        heaviest=max(bale.net_pounds for bale in bales),
        basis=basis,
        outliers=outliers,
    )


def outliers_in(book: Book, run_ref: str) -> tuple[tuple[str, int, Decimal], ...]:
    """Every bale off its run's basis, with how far off it is."""
    control = control_for(book, run_ref)
    found = []
    for tag in control.outliers:
        weight = book.bales.get(tag).net_pounds
        found.append((tag, weight, Decimal(weight) - control.basis))
    return tuple(sorted(found, key=lambda item: abs(item[2]), reverse=True))


def season_control(book: Book, crop_year: int) -> tuple[Control, ...]:
    """Every run in a crop year that has pressed something, worst first."""
    found = [control_for(book, run.ref) for run in runs_pressed(book, crop_year)]
    return tuple(sorted(found, key=lambda item: -abs(item.off_target)))
