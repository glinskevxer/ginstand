"""Printing a run's statements, one file per producer.

The office prints statements once and posts them, so the useful shape is a
folder of files named after the people they go to rather than one long document
somebody has to cut up.

Nothing is written until every statement has been worked out. A run where the
fourth producer's statement raises leaves three files on disk and a folder
somebody has to reason about, and the reasoning is always done by whoever finds
it a week later. So the whole run is built in memory first and written after,
which is a page or two of text and not worth being clever about.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ginstand.charges.tariff import Tariff
from ginstand.errors import StateError
from ginstand.report.settlement import producer_page
from ginstand.settle.gather import producers_in
from ginstand.store.book import Book
from ginstand.units.money import Money


@dataclass(frozen=True, slots=True)
class Printed:
    """One statement, written out."""

    producer: str
    path: Path
    lines: int

    @property
    def line(self) -> str:
        """The line the batch prints."""
        return f"{self.producer:<10} {self.lines:>4} lines  {self.path.name}"


def file_name(run_ref: str, producer: str) -> str:
    """What a producer's statement for a run is called."""
    return f"{run_ref.strip().upper()}-{producer.strip().upper()}.txt"


def build(
    book: Book,
    run_ref: str,
    tariff: Tariff,
    seed_price_per_ton: Money,
    on: date,
) -> dict[str, tuple[str, ...]]:
    """Every producer's statement for a run, worked out and not yet written."""
    who = producers_in(book, run_ref)
    if not who:
        raise StateError(f"nobody has cotton on gin run {run_ref.strip().upper()}")
    return {
        producer: producer_page(book, run_ref, producer, tariff, seed_price_per_ton, on)
        for producer in who
    }


def write(
    book: Book,
    run_ref: str,
    tariff: Tariff,
    seed_price_per_ton: Money,
    on: date,
    folder: Path,
) -> tuple[Printed, ...]:
    """Work every statement out, then write them."""
    if folder.exists() and not folder.is_dir():
        raise StateError(f"{folder} is a file, not a folder to write into")
    pages = build(book, run_ref, tariff, seed_price_per_ton, on)
    folder.mkdir(parents=True, exist_ok=True)
    printed = []
    for producer, lines in pages.items():
        path = folder / file_name(run_ref, producer)
        path.write_text("\n".join(lines) + "\n")
        printed.append(Printed(producer=producer, path=path, lines=len(lines)))
    return tuple(printed)
