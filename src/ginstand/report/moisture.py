"""Moisture at the two places it is read, and the dry matter between them.

Seed cotton comes in at one moisture and lint goes out at another, and the two
numbers on their own say nothing about each other. What connects them is the dry
matter: the water is driven off and put back, and what survives both is the
cotton.

So the report is not a comparison of two percentages. It is the dry matter in
what went in, the dry matter in what came out, and the ratio between them, which
is a turnout worked out on dry weight rather than on wet. That figure does not
move when the yard has a wet week, which is exactly why a gin manager reading
turnout across a season wants it.

A run's wet turnout and its dry turnout will differ. The gap is the moisture the
run carried, and a season where the gap is wide is a season where the wet
turnout is telling you about the weather.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ginstand.errors import StateError
from ginstand.ginning.season import runs_fed
from ginstand.report.table import Align, Column, Table
from ginstand.store.book import Book
from ginstand.units.apportion import proportion
from ginstand.units.moisture import SAFE_BALE_MOISTURE


@dataclass(frozen=True, slots=True)
class RunMoisture:
    """One run's moisture, in and out."""

    run: str
    modules: int
    seed_cotton_pounds: int
    seed_cotton_dry: int
    bales: int
    lint_pounds: int
    lint_dry: int
    wettest_module: Decimal
    wettest_bale: Decimal

    @property
    def mean_in(self) -> Decimal:
        """The weighted mean moisture of what went in."""
        return self._mean(self.seed_cotton_pounds, self.seed_cotton_dry)

    @property
    def mean_out(self) -> Decimal:
        """The weighted mean moisture of what came out."""
        return self._mean(self.lint_pounds, self.lint_dry)

    def _mean(self, wet: int, dry: int) -> Decimal:
        if wet == 0:
            return Decimal("0.0")
        return (Decimal(wet - dry) * 100 / wet).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

    @property
    def wet_turnout(self) -> Decimal:
        """Lint over seed cotton, both as weighed."""
        if self.seed_cotton_pounds == 0:
            return Decimal("0.0000")
        return proportion(self.lint_pounds, self.seed_cotton_pounds)

    @property
    def dry_turnout(self) -> Decimal:
        """Dry lint over dry seed cotton, which the weather does not move."""
        if self.seed_cotton_dry == 0:
            return Decimal("0.0000")
        return proportion(self.lint_dry, self.seed_cotton_dry)

    @property
    def gap(self) -> Decimal:
        """How far the two turnouts are apart, to four places."""
        return (self.dry_turnout - self.wet_turnout).quantize(Decimal("0.0001"))

    @property
    def over_ceiling(self) -> bool:
        """Whether any bale off this run was pressed above the storage ceiling."""
        return self.wettest_bale > SAFE_BALE_MOISTURE

    @property
    def line(self) -> str:
        """The line the moisture report prints."""
        flag = "  OVER CEILING" if self.over_ceiling else ""
        return (
            f"{self.run}  in {self.mean_in}%  out {self.mean_out}%  "
            f"wet {self.wet_turnout}  dry {self.dry_turnout}  gap {self.gap}{flag}"
        )


def for_run(book: Book, run_ref: str) -> RunMoisture:
    """One run's moisture, in and out."""
    run = book.runs.get(run_ref)
    modules = [book.modules.get(tag) for tag in book.runs.modules_in(run.ref)]
    if not modules:
        raise StateError(f"gin run {run.ref} has nothing in it")
    bales = book.bales.for_run(run.ref)
    return RunMoisture(
        run=run.ref,
        modules=len(modules),
        seed_cotton_pounds=sum(module.net_pounds for module in modules),
        seed_cotton_dry=sum(module.dry_pounds for module in modules),
        bales=len(bales),
        lint_pounds=sum(bale.net_pounds for bale in bales),
        lint_dry=sum(bale.dry_pounds for bale in bales),
        wettest_module=max(module.moisture_pct for module in modules),
        wettest_bale=max((bale.moisture_pct for bale in bales), default=Decimal("0.0")),
    )


def season(book: Book, crop_year: int) -> tuple[RunMoisture, ...]:
    """Every run in a crop year with cotton in it, widest gap first."""
    found = [for_run(book, run.ref) for run in runs_fed(book, crop_year)]
    return tuple(sorted(found, key=lambda item: -abs(item.gap)))


def moisture_table(book: Book, crop_year: int) -> Table:
    """Every run's moisture, widest gap between the turnouts first."""
    rows = tuple(
        (
            item.run,
            str(item.modules),
            f"{item.mean_in}%",
            str(item.wettest_module),
            str(item.bales),
            f"{item.mean_out}%",
            str(item.wettest_bale),
            str(item.wet_turnout),
            str(item.dry_turnout),
            str(item.gap),
            "over" if item.over_ceiling else "",
        )
        for item in season(book, crop_year)
    )
    return Table(
        title=f"Moisture, crop year {crop_year}",
        columns=(
            Column("run"),
            Column("modules", Align.RIGHT),
            Column("in", Align.RIGHT),
            Column("wettest", Align.RIGHT),
            Column("bales", Align.RIGHT),
            Column("out", Align.RIGHT),
            Column("wettest", Align.RIGHT),
            Column("wet turnout", Align.RIGHT),
            Column("dry turnout", Align.RIGHT),
            Column("gap", Align.RIGHT),
            Column("note"),
        ),
        rows=rows,
        empty_note="no run in this crop year has cotton in it",
    )
