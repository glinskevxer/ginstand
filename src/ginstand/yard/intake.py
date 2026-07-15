"""Reading a day's scale tickets off the weighbridge's own file.

A busy gin takes two hundred modules in a day and nobody types two hundred
tickets. The weighbridge writes a file, the office reads it, and the only thing
worth arguing about is what happens to the rows that will not go in.

They are kept, the same way a bad classing record is kept. A file of two hundred
tickets with three problems in it should put a hundred and ninety seven modules
in the book and print three lines, because the alternative is that the yard is
blocked until somebody at the weighbridge is reachable.

The file is comma separated rather than fixed width, because unlike the classing
office the weighbridge is ours and this is the format it was told to write.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from io import StringIO

from ginstand.errors import GinstandError, ValidationError
from ginstand.model.module import Module, ModuleKind, WrapKind
from ginstand.store.book import Book
from ginstand.yard.receiving import ScaleTicket, receive

COLUMNS = (
    "tag",
    "field",
    "kind",
    "wrap",
    "harvested",
    "received",
    "gross",
    "tare",
    "moisture",
)
"""The header the weighbridge writes, in order."""


@dataclass(frozen=True, slots=True)
class Problem:
    """One row that would not go in."""

    line_number: int
    tag: str
    message: str

    @property
    def line(self) -> str:
        """The problem as it prints on the intake report."""
        where = f" ({self.tag})" if self.tag else ""
        return f"line {self.line_number}{where}: {self.message}"


@dataclass(frozen=True, slots=True)
class Intake:
    """What a day's file came to."""

    tickets: tuple[ScaleTicket, ...]
    problems: tuple[Problem, ...]

    @property
    def clean(self) -> bool:
        """Whether every row went in."""
        return not self.problems

    @property
    def seed_cotton_pounds(self) -> int:
        """Every pound that crossed the scale."""
        return sum(ticket.net_pounds for ticket in self.tickets)

    @property
    def summary(self) -> str:
        """The line the office reads after an intake."""
        return (
            f"{len(self.tickets)} modules in, {self.seed_cotton_pounds:,} lb, "
            f"{len(self.problems)} problems"
        )


def parse_row(row: dict[str, str]) -> Module:
    """Turn one row of the file into a module."""
    for column in COLUMNS:
        if row.get(column) is None:
            raise ValidationError("row", f"has no {column} in it")
    return Module(
        tag=row["tag"],
        field=row["field"],
        kind=ModuleKind(row["kind"].strip().lower()),
        wrap=WrapKind(row["wrap"].strip().lower()),
        harvested=_day(row["harvested"], "harvested"),
        received=_day(row["received"], "received"),
        gross_pounds=_pounds(row["gross"], "gross weight"),
        tare_pounds=_pounds(row["tare"], "tare weight"),
        moisture_pct=_reading(row["moisture"]),
        variety=row.get("variety", "").strip(),
        note=row.get("note", "").strip(),
    )


def _day(text: str, field: str) -> date:
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        raise ValidationError(field, f"must be an ISO date, got {text!r}") from None


def _pounds(text: str, field: str) -> int:
    cleaned = text.strip().replace(",", "")
    if not cleaned.isdigit():
        raise ValidationError(field, f"must be whole pounds, got {text!r}")
    return int(cleaned)


def _reading(text: str) -> Decimal:
    try:
        return Decimal(text.strip())
    except InvalidOperation:
        raise ValidationError("moisture", f"is not a number: {text!r}") from None


def read(book: Book, text: str) -> Intake:
    """Read a day's file and weigh in everything that will go."""
    reader = csv.DictReader(StringIO(text))
    if reader.fieldnames is None:
        raise ValidationError("file", "has no header row")
    missing = [column for column in COLUMNS if column not in reader.fieldnames]
    if missing:
        raise ValidationError("file", f"has no {', '.join(missing)} column")

    tickets: list[ScaleTicket] = []
    problems: list[Problem] = []
    for number, row in enumerate(reader, start=2):
        tag = (row.get("tag") or "").strip()
        try:
            module = parse_row(row)
        except (GinstandError, ValueError) as exc:
            problems.append(Problem(line_number=number, tag=tag, message=str(exc)))
            continue
        try:
            tickets.append(receive(book, module))
        except GinstandError as exc:
            problems.append(Problem(line_number=number, tag=tag, message=str(exc)))
    return Intake(tickets=tuple(tickets), problems=tuple(problems))
