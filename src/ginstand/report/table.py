"""Printing a table of columns that line up.

Every report in this package is a table, and they all had their own column
widths worked out with format strings until one of them was widened and the
header stopped lining up with the body. Widths are measured off the content
here, once, and the header is measured with it.

Numbers go to the right and words go to the left. That is not a preference: a
column of right aligned numbers can be scanned for an odd one out and a column
of left aligned ones cannot.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum

from ginstand.errors import ValidationError


class Align(StrEnum):
    """Which side of the column the value sits against."""

    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True, slots=True)
class Column:
    """One column of a report."""

    header: str
    align: Align = Align.LEFT

    def cell(self, value: str, width: int) -> str:
        """Pad a value out to the column width."""
        return value.rjust(width) if self.align is Align.RIGHT else value.ljust(width)


@dataclass(frozen=True, slots=True)
class Table:
    """A heading, some columns and the rows under them."""

    columns: tuple[Column, ...]
    rows: tuple[tuple[str, ...], ...] = ()
    title: str = ""
    gap: str = "  "
    empty_note: str = "nothing to show"
    footers: tuple[tuple[str, ...], ...] = field(default=())

    def __post_init__(self) -> None:
        if not self.columns:
            raise ValidationError("table", "has no columns")
        for number, row in enumerate(self.rows, start=1):
            if len(row) != len(self.columns):
                raise ValidationError(
                    "table",
                    f"row {number} has {len(row)} cells and there are {len(self.columns)} columns",
                )
        for number, row in enumerate(self.footers, start=1):
            if len(row) != len(self.columns):
                raise ValidationError(
                    "table",
                    f"footer {number} has {len(row)} cells and there are "
                    f"{len(self.columns)} columns",
                )

    def widths(self) -> tuple[int, ...]:
        """How wide each column has to be for its header and every cell."""
        return tuple(
            max(
                len(column.header),
                *(len(row[index]) for row in self.rows + self.footers),
            )
            if self.rows or self.footers
            else len(column.header)
            for index, column in enumerate(self.columns)
        )

    def render(self) -> tuple[str, ...]:
        """The table as printable lines."""
        widths = self.widths()
        lines: list[str] = []
        if self.title:
            lines.append(self.title)
            lines.append("")
        lines.append(
            self.gap.join(
                column.cell(column.header, widths[index])
                for index, column in enumerate(self.columns)
            ).rstrip()
        )
        lines.append(self.gap.join("-" * width for width in widths))
        if not self.rows:
            lines.append(self.empty_note)
            return tuple(lines)
        lines.extend(self._body(self.rows, widths))
        if self.footers:
            lines.append(self.gap.join("-" * width for width in widths))
            lines.extend(self._body(self.footers, widths))
        return tuple(lines)

    def _body(self, rows: Sequence[tuple[str, ...]], widths: tuple[int, ...]) -> list[str]:
        return [
            self.gap.join(
                column.cell(row[index], widths[index]) for index, column in enumerate(self.columns)
            ).rstrip()
            for row in rows
        ]

    def text(self) -> str:
        """The table as one printable block."""
        return "\n".join(self.render())
