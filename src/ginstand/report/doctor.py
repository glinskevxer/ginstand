"""One command that asks everything worth asking about a book.

The office does not run seven checks. It runs one, in the morning, and it wants
a page that either says the book is fine or says what to go and look at.

So this is the other checks in a fixed order, with the structural questions
first. A book that is not a sound sqlite file has nothing worth saying about its
carries, and printing the carries anyway would bury the sentence that matters.

The exit is a count rather than a verdict. A gin office in October has open runs
and unclassed bales and that is not a problem, it is October, so nothing here
decides that a query is bad news. It counts them and lets somebody read.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ginstand.report.audit import Severity, audit
from ginstand.store.book import Book
from ginstand.store.maintenance import check as integrity_check
from ginstand.store.migrations import current_version, latest_version


@dataclass(frozen=True, slots=True)
class Diagnosis:
    """What the doctor found."""

    day: date
    schema: int
    expected: int
    structure: tuple[str, ...]
    faults: tuple[str, ...]
    queries: tuple[str, ...]

    @property
    def sound(self) -> bool:
        """Whether the book is structurally sound and at the right version."""
        return not self.structure and self.schema == self.expected

    @property
    def clean(self) -> bool:
        """Whether there is nothing at all to look at."""
        return self.sound and not self.faults and not self.queries

    @property
    def lines(self) -> tuple[str, ...]:
        """The page the doctor prints."""
        rows = [f"Book check at {self.day.isoformat()}", ""]
        if self.schema != self.expected:
            rows.append(f"  schema version {self.schema}, this code writes {self.expected}")
        else:
            rows.append(f"  schema version {self.schema}")
        if self.structure:
            rows.append("")
            rows.extend(f"  structure: {line}" for line in self.structure)
            rows.append("")
            rows.append("  nothing else was checked, because the file is not sound")
            return tuple(rows)
        rows.append("")
        rows.append(f"  {len(self.faults)} faults, {len(self.queries)} queries")
        rows.extend(f"  fault  {line}" for line in self.faults)
        rows.extend(f"  query  {line}" for line in self.queries)
        if self.clean:
            rows.append("")
            rows.append("  nothing to look at")
        return tuple(rows)


def diagnose(book: Book, on: date) -> Diagnosis:
    """Ask everything worth asking, structural questions first."""
    structure = integrity_check(book)
    schema = current_version(book.connection)
    if structure:
        return Diagnosis(
            day=on,
            schema=schema,
            expected=latest_version(),
            structure=structure,
            faults=(),
            queries=(),
        )
    notes = audit(book, on)
    return Diagnosis(
        day=on,
        schema=schema,
        expected=latest_version(),
        structure=(),
        faults=tuple(
            f"{note.subject}: {note.message}" for note in notes if note.severity is Severity.FAULT
        ),
        queries=tuple(
            f"{note.subject}: {note.message}" for note in notes if note.severity is Severity.QUERY
        ),
    )
