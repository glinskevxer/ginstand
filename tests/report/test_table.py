"""Widths come off the content, headers included, and numbers go right."""

from __future__ import annotations

import pytest

from ginstand.errors import ValidationError
from ginstand.report.table import Align, Column, Table

COLUMNS = (
    Column("tag"),
    Column("producer"),
    Column("pounds", Align.RIGHT),
)


def test_a_table_prints_a_header_and_a_rule() -> None:
    table = Table(columns=COLUMNS, rows=(("M-1", "Aldys", "22,060"),))
    lines = table.render()
    assert lines[0] == "tag  producer  pounds"
    assert lines[1] == "---  --------  ------"
    assert lines[2] == "M-1  Aldys     22,060"


def test_a_column_is_as_wide_as_its_widest_cell() -> None:
    table = Table(
        columns=COLUMNS,
        rows=(("M-1", "Aldys", "22,060"), ("M-2", "Merrick Land Co", "9,400")),
    )
    lines = table.render()
    assert lines[0] == "tag  producer         pounds"
    assert "Merrick Land Co" in lines[3]


def test_a_column_is_at_least_as_wide_as_its_header() -> None:
    table = Table(columns=(Column("producer"),), rows=(("A",),))
    lines = table.render()
    assert lines[0] == "producer"
    assert lines[2] == "A"


def test_numbers_go_to_the_right() -> None:
    table = Table(columns=(Column("pounds", Align.RIGHT),), rows=(("9",), ("22,060",)))
    lines = table.render()
    assert lines[2] == "     9"
    assert lines[3] == "22,060"


def test_trailing_space_is_trimmed_off_every_line() -> None:
    table = Table(columns=COLUMNS, rows=(("M-1", "Aldys", "1"),))
    for line in table.render():
        assert line == line.rstrip()


def test_a_title_is_printed_with_a_blank_line_under_it() -> None:
    table = Table(columns=COLUMNS, rows=(("M-1", "A", "1"),), title="Yard standing")
    lines = table.render()
    assert lines[0] == "Yard standing"
    assert lines[1] == ""
    assert lines[2].startswith("tag")


def test_an_empty_table_says_so_rather_than_printing_nothing() -> None:
    table = Table(columns=COLUMNS, empty_note="the yard is empty")
    lines = table.render()
    assert lines[-1] == "the yard is empty"
    assert len(lines) == 3


def test_a_footer_is_ruled_off_from_the_body() -> None:
    table = Table(
        columns=COLUMNS,
        rows=(("M-1", "Aldys", "22,060"), ("M-2", "Aldys", "9,400")),
        footers=(("", "total", "31,460"),),
    )
    lines = table.render()
    assert lines[-2].startswith("---")
    assert lines[-1].endswith("31,460")


def test_a_footer_widens_a_column_like_a_row_does() -> None:
    table = Table(
        columns=(Column("n", Align.RIGHT),),
        rows=(("1",),),
        footers=(("1,000,000",),),
    )
    assert table.render()[0] == "        n"


def test_a_row_with_the_wrong_number_of_cells_is_refused() -> None:
    with pytest.raises(ValidationError, match="row 1 has 2 cells and there are 3"):
        Table(columns=COLUMNS, rows=(("M-1", "Aldys"),))


def test_a_footer_with_the_wrong_number_of_cells_is_refused() -> None:
    with pytest.raises(ValidationError, match="footer 1 has 1 cells"):
        Table(columns=COLUMNS, footers=(("total",),))


def test_a_table_with_no_columns_is_refused() -> None:
    with pytest.raises(ValidationError, match="has no columns"):
        Table(columns=())


def test_the_gap_between_columns_can_be_widened() -> None:
    table = Table(columns=COLUMNS, rows=(("M-1", "A", "1"),), gap=" | ")
    assert table.render()[0] == "tag | producer | pounds"


def test_the_block_form_joins_the_lines() -> None:
    table = Table(columns=COLUMNS, rows=(("M-1", "A", "1"),))
    assert table.text() == "\n".join(table.render())
