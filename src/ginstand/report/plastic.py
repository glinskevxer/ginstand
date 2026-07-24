"""Where the plastic came from.

A plastic note on a classing card is the most expensive line in this package. It
condemns the bale, and if it keeps happening it costs the gin its buyers. So the
question is never whether a bale had plastic in it, it is which module put it
there, and the answer is a walk backwards from the card.

The walk is honest about what it can and cannot say. A run that had film wrapped
modules in it has a plain suspect list, and the yield is the fraction of that
run's bales that came back with a plastic note. A run with no film in it and a
plastic note on a bale is a different problem entirely: the film did not come
off a module, so it came off the yard, the feeder or somebody's coat, and that
is worth knowing precisely because the usual answer is wrong.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from ginstand.ginning.season import runs_pressed
from ginstand.grades.matter import ExtraneousKind
from ginstand.model.classing import Classing
from ginstand.report.table import Align, Column, Table
from ginstand.store.book import Book


@dataclass(frozen=True, slots=True)
class RunPlastic:
    """One run's plastic record."""

    run: str
    bales: int
    flagged: int
    heavy: int
    film_modules: tuple[str, ...]
    other_modules: tuple[str, ...]

    @property
    def rate(self) -> Decimal:
        """The share of the run's bales that came back with a plastic note."""
        if self.bales == 0:
            return Decimal("0.00")
        return (Decimal(self.flagged) * 100 / self.bales).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @property
    def had_film(self) -> bool:
        """Whether any module in the run was wrapped in film."""
        return bool(self.film_modules)

    @property
    def unexplained(self) -> bool:
        """Whether plastic turned up on a run with no film in it.

        This is the finding worth acting on. Film off a wrap is a known problem
        with a known fix. Plastic with no film anywhere in the run came from
        somewhere nobody is watching.
        """
        return self.flagged > 0 and not self.had_film

    @property
    def line(self) -> str:
        """The line the report prints."""
        source = f"{len(self.film_modules)} film modules" if self.had_film else "no film in the run"
        flag = "  UNEXPLAINED" if self.unexplained else ""
        return f"{self.run}  {self.flagged}/{self.bales} bales ({self.rate}%)  {source}{flag}"


def carries_plastic(card: Classing) -> bool:
    """Whether a card notes plastic at either level."""
    return any(note.kind is ExtraneousKind.PLASTIC for note in card.extraneous)


def heavy_plastic(card: Classing) -> bool:
    """Whether a card notes plastic at the level that condemns the bale."""
    return any(note.kind is ExtraneousKind.PLASTIC and note.heavy for note in card.extraneous)


def for_run(book: Book, run_ref: str) -> RunPlastic:
    """One run's plastic record, with the modules that could have caused it."""
    run = book.runs.get(run_ref)
    film: list[str] = []
    other: list[str] = []
    for tag in book.runs.modules_in(run.ref):
        module = book.modules.get(tag)
        (film if module.carries_plastic else other).append(module.tag)

    bales = book.bales.for_run(run.ref)
    flagged = 0
    heavy = 0
    for bale in bales:
        card = book.cards.find(bale.tag)
        if card is None:
            continue
        if carries_plastic(card):
            flagged += 1
        if heavy_plastic(card):
            heavy += 1
    return RunPlastic(
        run=run.ref,
        bales=len(bales),
        flagged=flagged,
        heavy=heavy,
        film_modules=tuple(film),
        other_modules=tuple(other),
    )


def season(book: Book, crop_year: int) -> tuple[RunPlastic, ...]:
    """Every run in a crop year that saw plastic, worst rate first."""
    found = [for_run(book, run.ref) for run in runs_pressed(book, crop_year)]
    return tuple(sorted((item for item in found if item.flagged), key=lambda i: -i.rate))


def suspects(book: Book, tag: str) -> tuple[str, ...]:
    """The film wrapped modules that were in the run this bale came off."""
    bale = book.bales.get(tag)
    return for_run(book, bale.run).film_modules


def fields_behind(book: Book, run_ref: str) -> tuple[str, ...]:
    """Every field whose film wrapped cotton went into a run, in reference order."""
    return tuple(
        sorted({book.modules.get(tag).field for tag in for_run(book, run_ref).film_modules})
    )


def plastic_table(book: Book, crop_year: int) -> Table:
    """Every run that saw plastic, worst first."""
    rows = tuple(
        (
            item.run,
            str(item.bales),
            str(item.flagged),
            str(item.heavy),
            f"{item.rate}%",
            str(len(item.film_modules)),
            ", ".join(fields_behind(book, item.run)),
            "unexplained" if item.unexplained else "",
        )
        for item in season(book, crop_year)
    )
    return Table(
        title=f"Plastic, crop year {crop_year}",
        columns=(
            Column("run"),
            Column("bales", Align.RIGHT),
            Column("noted", Align.RIGHT),
            Column("heavy", Align.RIGHT),
            Column("rate", Align.RIGHT),
            Column("film", Align.RIGHT),
            Column("fields"),
            Column("note"),
        ),
        rows=rows,
        empty_note="no bale came back with a plastic note",
    )
