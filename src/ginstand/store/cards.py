"""Reading and writing classing cards.

A card arrives against a bale that is already in the book, so the table has a
foreign key to it and no card can exist for a bale nobody pressed. That has
caught a mistyped tag on a classing file more than once, which is exactly the
sort of error that is cheap now and expensive at settlement.

Extraneous matter is stored as its printed codes, space separated. It is a short
list from a fixed vocabulary, it reads correctly in a database browser, and the
alternative is a second table that would never be queried on its own.
"""

from __future__ import annotations

import sqlite3

from ginstand.errors import DuplicateError, NotFoundError
from ginstand.grades.color import ColorGrade
from ginstand.grades.matter import Extraneous, parse_extraneous
from ginstand.ids import bale_tag
from ginstand.model.classing import Classing
from ginstand.store.repository import Repository
from ginstand.store.sqlite import as_date, as_decimal


class CardStore(Repository[Classing]):
    """The classing cards the office has sent back."""

    table = "classing"
    kind = "classing card"
    key_column = "tag"
    order_by = "tag"

    def _key(self, value: str) -> str:
        return bale_tag(value)

    def _from_row(self, row: sqlite3.Row) -> Classing:
        return _card_from(row)

    def add(self, card: Classing) -> None:
        """File a card against a bale. Raises if the bale already has one."""
        if self.exists(card.tag):
            raise DuplicateError("classing card", card.tag)
        self._connection.execute(
            "INSERT INTO classing (tag, classed, color, leaf, staple, micronaire, strength,"
            " uniformity, trash_pct, extraneous, office, remarks)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                card.tag,
                card.classed.isoformat(),
                card.color.code,
                card.leaf,
                card.staple,
                str(card.micronaire),
                str(card.strength),
                str(card.uniformity),
                str(card.trash_pct),
                card.codes,
                card.office,
                card.remarks,
            ),
        )

    def replace(self, card: Classing) -> None:
        """Replace a card after a recheck. Raises if there was no card."""
        if not self.exists(card.tag):
            raise NotFoundError("classing card", card.tag)
        self._connection.execute(
            "UPDATE classing SET classed = ?, color = ?, leaf = ?, staple = ?, micronaire = ?,"
            " strength = ?, uniformity = ?, trash_pct = ?, extraneous = ?, office = ?,"
            " remarks = ? WHERE tag = ?",
            (
                card.classed.isoformat(),
                card.color.code,
                card.leaf,
                card.staple,
                str(card.micronaire),
                str(card.strength),
                str(card.uniformity),
                str(card.trash_pct),
                card.codes,
                card.office,
                card.remarks,
                card.tag,
            ),
        )

    def for_run(self, run: str) -> tuple[Classing, ...]:
        """Every card against a bale off one run."""
        rows = self._connection.execute(
            "SELECT c.* FROM classing c JOIN bale b ON b.tag = c.tag"
            " WHERE b.run = ? ORDER BY c.tag",
            (run.strip().upper(),),
        ).fetchall()
        return tuple(_card_from(row) for row in rows)

    def unclassed_tags(self) -> tuple[str, ...]:
        """Every bale in the book with no card against it yet."""
        rows = self._connection.execute(
            "SELECT b.tag FROM bale b LEFT JOIN classing c ON c.tag = b.tag"
            " WHERE c.tag IS NULL ORDER BY b.tag"
        ).fetchall()
        return tuple(str(row["tag"]) for row in rows)


def _notes(text: str) -> tuple[Extraneous, ...]:
    return tuple(parse_extraneous(code) for code in text.split())


def _card_from(row: sqlite3.Row) -> Classing:
    return Classing(
        tag=str(row["tag"]),
        classed=as_date(row["classed"]),
        color=ColorGrade(int(row["color"])),
        leaf=int(row["leaf"]),
        staple=int(row["staple"]),
        micronaire=as_decimal(row["micronaire"]),
        strength=as_decimal(row["strength"]),
        uniformity=as_decimal(row["uniformity"]),
        trash_pct=as_decimal(row["trash_pct"]),
        extraneous=_notes(str(row["extraneous"])),
        office=str(row["office"]),
        remarks=str(row["remarks"]),
    )
