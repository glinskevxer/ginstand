"""What each field yielded.

The producer's first question about a settlement is not about the money, it is
about the yield: bales an acre off that field, and how it compares with the one
next to it. So the field report is the one the office prints most often after
the statement itself.

Lint per acre is the honest figure and bales per acre is the one everybody
quotes. Both are here, because a field of light bales and a field of heavy ones
give the same bale count off very different crops.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ginstand.errors import StateError
from ginstand.ginning.season import runs_fed
from ginstand.report.table import Align, Column, Table
from ginstand.store.book import Book
from ginstand.units.apportion import apportion, proportion


@dataclass(frozen=True, slots=True)
class FieldYield:
    """One field's crop for a crop year."""

    field: str
    name: str
    acres: Decimal
    variety: str
    irrigated: bool
    modules: int
    seed_cotton_pounds: int
    lint_pounds: int
    bales: Decimal

    @property
    def bales_per_acre(self) -> Decimal:
        """Bales an acre, to two places."""
        return (self.bales / self.acres).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def lint_per_acre(self) -> Decimal:
        """Pounds of lint an acre, to one place."""
        return (Decimal(self.lint_pounds) / self.acres).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )

    @property
    def turnout(self) -> Decimal:
        """Lint over seed cotton off this field."""
        if self.seed_cotton_pounds == 0:
            return Decimal("0.0000")
        return proportion(self.lint_pounds, self.seed_cotton_pounds)


def yields(book: Book, crop_year: int) -> tuple[FieldYield, ...]:
    """Every field that fed a run in a crop year, best yield first.

    A field's lint is worked out by splitting each run's lint between the fields
    that fed it, pro rata by seed cotton. That is an estimate and it is the only
    one available: the gin does not keep a run's cotton separated by field, and
    a producer who wants a field graded on its own has to gin it on its own.
    """
    seed_cotton: dict[str, int] = {}
    modules: dict[str, int] = {}
    lint: dict[str, int] = {}

    for run in runs_fed(book, crop_year):
        tags = book.runs.modules_in(run.ref)
        by_field: dict[str, int] = {}
        for tag in tags:
            module = book.modules.get(tag)
            by_field[module.field] = by_field.get(module.field, 0) + module.net_pounds
            modules[module.field] = modules.get(module.field, 0) + 1
            seed_cotton[module.field] = seed_cotton.get(module.field, 0) + module.net_pounds
        fields = list(by_field)
        shares = apportion(
            book.bales.lint_pounds_for_run(run.ref), [by_field[key] for key in fields]
        )
        for key, share in zip(fields, shares, strict=True):
            lint[key] = lint.get(key, 0) + share

    found = []
    for ref in sorted(seed_cotton):
        plot = book.fields.get(ref)
        pounds = lint.get(ref, 0)
        found.append(
            FieldYield(
                field=plot.ref,
                name=plot.name,
                acres=plot.acres,
                variety=plot.variety,
                irrigated=plot.irrigated,
                modules=modules.get(ref, 0),
                seed_cotton_pounds=seed_cotton[ref],
                lint_pounds=pounds,
                bales=(Decimal(pounds) / 480).quantize(Decimal("0.01")),
            )
        )
    return tuple(sorted(found, key=lambda item: -item.lint_per_acre))


def yield_table(book: Book, crop_year: int) -> Table:
    """Every field's yield, best first."""
    rows = tuple(
        (
            item.field,
            item.name,
            str(item.acres),
            item.variety,
            "yes" if item.irrigated else "",
            str(item.modules),
            f"{item.seed_cotton_pounds:,}",
            f"{item.lint_pounds:,}",
            str(item.turnout),
            str(item.bales_per_acre),
            str(item.lint_per_acre),
        )
        for item in yields(book, crop_year)
    )
    return Table(
        title=f"Field yields, crop year {crop_year}",
        columns=(
            Column("field"),
            Column("name"),
            Column("acres", Align.RIGHT),
            Column("variety"),
            Column("irr"),
            Column("modules", Align.RIGHT),
            Column("seed cotton", Align.RIGHT),
            Column("lint", Align.RIGHT),
            Column("turnout", Align.RIGHT),
            Column("bales/ac", Align.RIGHT),
            Column("lint/ac", Align.RIGHT),
        ),
        rows=rows,
        empty_note="no field fed a run in this crop year",
    )


def best(book: Book, crop_year: int) -> FieldYield:
    """The field that yielded most lint an acre."""
    found = yields(book, crop_year)
    if not found:
        raise StateError(f"no field fed a run in crop year {crop_year}")
    return found[0]
