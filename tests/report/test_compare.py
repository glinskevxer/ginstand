"""Two crop years, and a blank where there is nothing to compare against."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.grades.color import ColorGrade
from ginstand.model.classing import Classing
from ginstand.report.compare import compare, rows
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

from .conftest import a_module


def a_year(
    book: Book, ref: str, crop_year: int, seed_cotton: int, bales: int, classed: bool = True
) -> None:
    day = date(crop_year, 10, 14)
    open_run(book, ref, "41207", day)
    tag = f"M-{ref}"
    receive(
        book,
        a_module(
            tag,
            gross_pounds=26_140 + seed_cotton,
            tare_pounds=26_140,
            harvested=date(crop_year, 9, 28),
            received=date(crop_year, 10, 2),
        ),
    )
    feed(book, ref, tag, day)
    for _ in range(bales):
        bale = press(book, ref, day, 512, 22, Decimal("6.8"))
        if classed:
            book.cards.add(
                Classing(
                    tag=bale.tag,
                    classed=date(crop_year, 10, 22),
                    color=ColorGrade(31),
                    leaf=3,
                    staple=35,
                    micronaire=Decimal("4.3"),
                    strength=Decimal("29.4"),
                    uniformity=Decimal("81.2"),
                )
            )
    close_run(book, ref, day)


def figures(book: Book, earlier: int, later: int) -> dict[str, str]:
    return {row.label: row.change for row in rows(book, earlier, later)}


def test_two_years_with_nothing_in_them_compare_to_nothing(book: Book) -> None:
    for row in rows(book, 2025, 2026):
        assert row.earlier == ""
        assert row.later == ""
        assert not row.comparable


def test_a_year_with_nothing_to_compare_against_shows_no_change(book: Book) -> None:
    a_year(book, "GR-1", 2025, 20_000, 14)
    found = {row.label: row for row in rows(book, 2024, 2025)}
    assert found["bales"].earlier == ""
    assert found["bales"].later == "14"
    assert not found["bales"].comparable


def test_two_years_side_by_side_show_the_change(book: Book) -> None:
    a_year(book, "GR-1", 2025, 20_000, 14)
    a_year(book, "GR-2", 2026, 20_000, 20)
    assert figures(book, 2025, 2026)["bales"] == "+6"


def test_a_fall_carries_its_sign(book: Book) -> None:
    a_year(book, "GR-1", 2025, 20_000, 20)
    a_year(book, "GR-2", 2026, 20_000, 14)
    assert figures(book, 2025, 2026)["bales"] == "-6"


def test_the_turnout_change_carries_its_places(book: Book) -> None:
    a_year(book, "GR-1", 2025, 20_000, 14)
    a_year(book, "GR-2", 2026, 20_000, 20)
    change = figures(book, 2025, 2026)["lint turnout"]
    assert change.startswith("+0.")


def test_the_classing_figures_are_blank_where_nothing_was_classed(
    book: Book,
) -> None:
    a_year(book, "GR-1", 2025, 20_000, 14, classed=False)
    a_year(book, "GR-2", 2026, 20_000, 14)
    found = {row.label: row for row in rows(book, 2025, 2026)}
    assert found["staple"].earlier == ""
    assert found["staple"].later == "35.00"
    assert not found["staple"].comparable


def test_the_loan_rate_is_blank_where_nothing_was_priced(book: Book) -> None:
    a_year(book, "GR-1", 2025, 20_000, 14, classed=False)
    found = {row.label: row for row in rows(book, 2025, 2026)}
    assert found["loan rate"].earlier == ""


def test_the_downtime_is_blank_where_nothing_was_logged(book: Book) -> None:
    a_year(book, "GR-1", 2025, 20_000, 14)
    found = {row.label: row for row in rows(book, 2025, 2026)}
    assert found["minutes stopped"].earlier == ""


def test_there_are_eight_figures_and_no_way_to_add_a_ninth(book: Book) -> None:
    assert len(rows(book, 2025, 2026)) == 8


def test_the_table_names_both_years_in_its_columns(book: Book) -> None:
    a_year(book, "GR-1", 2025, 20_000, 14)
    text = compare(book, 2025, 2026).text()
    assert "Crop year 2025 against 2026" in text
    assert "2025" in text
    assert "2026" in text


@pytest.mark.parametrize(
    "label",
    ["bales", "seed cotton", "lint turnout", "staple", "micronaire", "loan rate"],
)
def test_every_figure_a_manager_would_put_side_by_side_is_there(book: Book, label: str) -> None:
    assert label in {row.label for row in rows(book, 2025, 2026)}
