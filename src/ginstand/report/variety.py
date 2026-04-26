"""How each variety did.

A producer choosing what to plant next year asks the gin, because the gin is the
only place the yield and the classing sit in the same book. So the variety
report puts turnout, lint per acre and classing side by side, weighted by weight
throughout.

The report says what it cannot tell you as well as what it can. A bale comes off
a run that mixed fields, so its variety is the run's variety and not the bale's,
and a run that mixed two varieties is left out of the classing figures rather
than assigned to either. And a variety grown on the two best fields on the place
looks good here whatever it is, so the field count is on the line and a variety
grown on too few of them is marked thin.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from ginstand.loan.schedule import Schedule, schedule_for
from ginstand.loan.value import value_bale
from ginstand.report.field import yields
from ginstand.report.table import Align, Column, Table
from ginstand.store.book import Book
from ginstand.units.apportion import proportion
from ginstand.units.money import Money, format_money

MINIMUM_FIELDS = 3
"""Below this many fields, a variety's figures are one field's figures."""

UNRECORDED = "unrecorded"
"""What a field with no variety on it is grouped under."""


@dataclass
class _Ground:
    """What a variety was grown on."""

    fields: int = 0
    acres: Decimal = field(default_factory=lambda: Decimal("0"))
    modules: int = 0
    seed_cotton: int = 0
    lint: int = 0


@dataclass
class _Classing:
    """What a variety classed, weighted by bale weight."""

    bales: int = 0
    weight: int = 0
    staple: Decimal = field(default_factory=lambda: Decimal("0"))
    micronaire: Decimal = field(default_factory=lambda: Decimal("0"))
    loan_value: Money = field(default_factory=lambda: Money(0))
    loan_pounds: int = 0

    def mean_staple(self) -> Decimal:
        """The weighted mean staple, or zero where nothing was classed."""
        return self._mean(self.staple)

    def mean_micronaire(self) -> Decimal:
        """The weighted mean micronaire, or zero where nothing was classed."""
        return self._mean(self.micronaire)

    def _mean(self, total: Decimal) -> Decimal:
        if self.weight == 0:
            return Decimal("0.00")
        return (total / self.weight).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True, slots=True)
class VarietyLine:
    """One variety's season."""

    variety: str
    fields: int
    acres: Decimal
    modules: int
    seed_cotton_pounds: int
    lint_pounds: int
    classed_bales: int
    staple: Decimal
    micronaire: Decimal
    loan_value: Money
    loan_pounds: int

    @property
    def turnout(self) -> Decimal:
        """Lint over seed cotton for this variety."""
        if self.seed_cotton_pounds == 0:
            return Decimal("0.0000")
        return proportion(self.lint_pounds, self.seed_cotton_pounds)

    @property
    def lint_per_acre(self) -> Decimal:
        """Pounds of lint an acre."""
        if self.acres == 0:
            return Decimal("0.0")
        return (Decimal(self.lint_pounds) / self.acres).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )

    @property
    def loan_rate(self) -> Decimal:
        """Cents a pound across the bales the loan would take."""
        if self.loan_pounds == 0:
            return Decimal("0.0000")
        return (Decimal(self.loan_value) / self.loan_pounds).quantize(
            Decimal("0.0001"), rounding=ROUND_HALF_UP
        )

    @property
    def thin(self) -> bool:
        """Whether this variety was grown on too few fields to compare."""
        return self.fields < MINIMUM_FIELDS


def variety_of_run(book: Book, run_ref: str) -> str | None:
    """The one variety a run was fed on, or None where it mixed two."""
    varieties = {
        book.fields.get(book.modules.get(tag).field).variety or UNRECORDED
        for tag in book.runs.modules_in(run_ref)
    }
    return varieties.pop() if len(varieties) == 1 else None


def _ground(book: Book, crop_year: int) -> dict[str, _Ground]:
    found: dict[str, _Ground] = {}
    for item in yields(book, crop_year):
        plot = book.fields.get(item.field)
        ground = found.setdefault(plot.variety or UNRECORDED, _Ground())
        ground.fields += 1
        ground.acres += plot.acres
        ground.modules += item.modules
        ground.seed_cotton += item.seed_cotton_pounds
        ground.lint += item.lint_pounds
    return found


def _classing(book: Book, crop_year: int, schedule: Schedule) -> dict[str, _Classing]:
    found: dict[str, _Classing] = {}
    for run in book.runs.for_crop_year(crop_year):
        name = variety_of_run(book, run.ref)
        if name is None:
            continue
        for bale in book.bales.for_run(run.ref):
            card = book.cards.find(bale.tag)
            if card is None:
                continue
            classing = found.setdefault(name, _Classing())
            classing.bales += 1
            classing.weight += bale.net_pounds
            classing.staple += Decimal(card.staple) * bale.net_pounds
            classing.micronaire += card.micronaire * bale.net_pounds
            valuation = value_bale(schedule, card, bale.net_pounds)
            if valuation.eligible:
                classing.loan_value = Money(classing.loan_value + valuation.value)
                classing.loan_pounds += bale.net_pounds
    return found


def lines(book: Book, crop_year: int) -> tuple[VarietyLine, ...]:
    """Every variety that fed a run in a crop year, best lint per acre first."""
    schedule = schedule_for(crop_year)
    ground = _ground(book, crop_year)
    classing = _classing(book, crop_year, schedule)
    built = [
        VarietyLine(
            variety=name,
            fields=grown.fields,
            acres=grown.acres,
            modules=grown.modules,
            seed_cotton_pounds=grown.seed_cotton,
            lint_pounds=grown.lint,
            classed_bales=classing.get(name, _Classing()).bales,
            staple=classing.get(name, _Classing()).mean_staple(),
            micronaire=classing.get(name, _Classing()).mean_micronaire(),
            loan_value=classing.get(name, _Classing()).loan_value,
            loan_pounds=classing.get(name, _Classing()).loan_pounds,
        )
        for name, grown in ground.items()
    ]
    return tuple(sorted(built, key=lambda item: -item.lint_per_acre))


def variety_table(book: Book, crop_year: int) -> Table:
    """Every variety, best lint per acre first."""
    rows = tuple(
        (
            item.variety,
            f"{item.fields} thin" if item.thin else str(item.fields),
            str(item.acres),
            f"{item.seed_cotton_pounds:,}",
            f"{item.lint_pounds:,}",
            str(item.turnout),
            str(item.lint_per_acre),
            str(item.classed_bales),
            str(item.staple),
            str(item.micronaire),
            format_money(item.loan_value),
        )
        for item in lines(book, crop_year)
    )
    return Table(
        title=f"Varieties, crop year {crop_year}",
        columns=(
            Column("variety"),
            Column("fields", Align.RIGHT),
            Column("acres", Align.RIGHT),
            Column("seed cotton", Align.RIGHT),
            Column("lint", Align.RIGHT),
            Column("turnout", Align.RIGHT),
            Column("lint/ac", Align.RIGHT),
            Column("classed", Align.RIGHT),
            Column("staple", Align.RIGHT),
            Column("mic", Align.RIGHT),
            Column("loan", Align.RIGHT),
        ),
        rows=rows,
        empty_note="no variety fed a run in this crop year",
    )
