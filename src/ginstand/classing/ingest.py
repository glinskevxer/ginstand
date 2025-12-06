"""Reading the classing file the office sends back.

The file is fixed width, one record per bale, and it has not changed shape in
thirty years. Every numeric field carries an implied decimal place: micronaire
043 is 4.3, strength 294 is 29.4. Nothing in the file says so, which is the
whole reason this module exists rather than a split on commas somewhere.

A bad record does not stop the read. A gin gets one file a day with four hundred
records in it, and a reader that stops on the first bad one turns a morning into
an afternoon. Every record is either a card or a problem with a line number
against it, and the caller decides what to do about the problems.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ginstand.errors import GinstandError, ValidationError
from ginstand.grades.color import ColorGrade
from ginstand.grades.matter import Extraneous, parse_extraneous
from ginstand.model.classing import Classing

RECORD_WIDTH = 50
"""Everything up to the remarks, which run to the end of the line."""

FIELDS = {
    "tag": (0, 12),
    "classed": (12, 20),
    "colour": (20, 22),
    "leaf": (22, 23),
    "staple": (23, 25),
    "micronaire": (25, 28),
    "strength": (28, 31),
    "uniformity": (31, 34),
    "trash": (34, 37),
    "extraneous": (37, 46),
    "office": (46, 50),
}
"""Half open character ranges, counted from zero."""


@dataclass(frozen=True, slots=True)
class Problem:
    """One record that could not be read."""

    line_number: int
    text: str
    message: str

    @property
    def line(self) -> str:
        """The problem as it prints on the read report."""
        return f"line {self.line_number}: {self.message}"


@dataclass(frozen=True, slots=True)
class Reading:
    """What came out of a classing file."""

    cards: tuple[Classing, ...]
    problems: tuple[Problem, ...]

    @property
    def clean(self) -> bool:
        """Whether every record read."""
        return not self.problems

    @property
    def summary(self) -> str:
        """The line the office prints after a read."""
        return f"{len(self.cards)} cards read, {len(self.problems)} problems"


def _slice(text: str, name: str) -> str:
    start, end = FIELDS[name]
    return text[start:end].strip()


def _implied(text: str, name: str) -> Decimal:
    digits = text.strip()
    if not digits.isdigit():
        raise ValidationError(name, f"must be digits with an implied place, got {text!r}")
    return Decimal(digits) / 10


def parse_record(text: str) -> Classing:
    """Read one fixed width record into a card."""
    record = text.rstrip("\r\n")
    if len(record) < RECORD_WIDTH:
        raise ValidationError(
            "record", f"is {len(record)} characters, expected at least {RECORD_WIDTH}"
        )
    classed = _slice(text, "classed")
    if len(classed) != 8 or not classed.isdigit():
        raise ValidationError("classed", f"must be eight digits, got {classed!r}")
    colour = _slice(text, "colour")
    if not colour.isdigit():
        raise ValidationError("colour grade", f"must be two digits, got {colour!r}")
    leaf = _slice(text, "leaf")
    if not leaf.isdigit():
        raise ValidationError("leaf grade", f"must be a digit, got {leaf!r}")
    staple = _slice(text, "staple")
    if not staple.isdigit():
        raise ValidationError("staple", f"must be two digits, got {staple!r}")
    return Classing(
        tag=_slice(text, "tag"),
        classed=date(int(classed[:4]), int(classed[4:6]), int(classed[6:])),
        color=ColorGrade(int(colour)),
        leaf=int(leaf),
        staple=int(staple),
        micronaire=_implied(_slice(text, "micronaire"), "micronaire"),
        strength=_implied(_slice(text, "strength"), "strength"),
        uniformity=_implied(_slice(text, "uniformity"), "uniformity"),
        trash_pct=_implied(_slice(text, "trash"), "trash"),
        extraneous=_extraneous(text),
        office=_slice(text, "office"),
        remarks=text[RECORD_WIDTH:].strip(),
    )


def _extraneous(text: str) -> tuple[Extraneous, ...]:
    start, end = FIELDS["extraneous"]
    block = text[start:end]
    notes = []
    for offset in range(0, end - start, 3):
        code = block[offset : offset + 3].strip()
        if code:
            notes.append(parse_extraneous(code))
    return tuple(notes)


def read(text: str) -> Reading:
    """Read a whole classing file, keeping the problems rather than stopping."""
    cards: list[Classing] = []
    problems: list[Problem] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            cards.append(parse_record(line))
        except GinstandError as exc:
            problems.append(Problem(line_number=number, text=line, message=str(exc)))
    return Reading(cards=tuple(cards), problems=tuple(problems))
