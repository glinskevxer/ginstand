"""Variety comparison, and what it says it cannot tell you."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.grades.color import ColorGrade
from ginstand.model.classing import Classing
from ginstand.model.farm import Field
from ginstand.report.variety import MINIMUM_FIELDS, lines, variety_of_run, variety_table
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

from .conftest import a_module

OPENED = date(2025, 10, 14)


def plant(book: Book, ref: str, variety: str, acres: str = "40") -> None:
    book.fields.add(
        Field(
            ref=ref,
            farm="F-3",
            name=ref,
            acres=Decimal(acres),
            lease="L-1",
            variety=variety,
        )
    )


def a_run(
    book: Book,
    ref: str,
    feeds: tuple[tuple[str, str, int], ...],
    bales: int,
    day: date = OPENED,
    classed: bool = True,
) -> None:
    open_run(book, ref, "41207", day)
    for tag, field_ref, net in feeds:
        receive(
            book,
            a_module(tag, field=field_ref, gross_pounds=26_140 + net, tare_pounds=26_140),
        )
        feed(book, ref, tag, day)
    for _ in range(bales):
        bale = press(book, ref, day, 512, 22, Decimal("6.8"))
        if classed:
            book.cards.add(
                Classing(
                    tag=bale.tag,
                    classed=date(2025, 10, 22),
                    color=ColorGrade(31),
                    leaf=3,
                    staple=35,
                    micronaire=Decimal("4.3"),
                    strength=Decimal("29.4"),
                    uniformity=Decimal("81.2"),
                )
            )
    close_run(book, ref, day)


def test_a_crop_year_nobody_ginned_has_no_varieties(book: Book) -> None:
    assert lines(book, 2025) == ()
    assert variety_table(book, 2025).render()[-1] == "no variety fed a run in this crop year"


def test_a_variety_gathers_its_fields(book: Book) -> None:
    plant(book, "FL-1", "DP 2115")
    plant(book, "FL-2", "DP 2115")
    a_run(book, "GR-1", (("M-1", "FL-1", 10_000), ("M-2", "FL-2", 10_000)), 14)
    found = lines(book, 2025)
    assert len(found) == 1
    assert found[0].variety == "DP 2115"
    assert found[0].fields == 2
    assert found[0].acres == Decimal("80.00")


def test_a_field_with_no_variety_is_grouped_as_unrecorded(book: Book) -> None:
    a_run(book, "GR-1", (("M-1", "FL-9", 10_000),), 14)
    assert lines(book, 2025)[0].variety == "unrecorded"


def test_two_varieties_are_kept_apart(book: Book) -> None:
    plant(book, "FL-1", "DP 2115")
    plant(book, "FL-2", "ST 4990")
    a_run(book, "GR-1", (("M-1", "FL-1", 10_000),), 14)
    a_run(book, "GR-2", (("M-2", "FL-2", 10_000),), 10, day=date(2025, 10, 20))
    assert {item.variety for item in lines(book, 2025)} == {"DP 2115", "ST 4990"}


def test_the_best_lint_per_acre_is_listed_first(book: Book) -> None:
    plant(book, "FL-1", "DP 2115")
    plant(book, "FL-2", "ST 4990")
    a_run(book, "GR-1", (("M-1", "FL-1", 10_000),), 14)
    a_run(book, "GR-2", (("M-2", "FL-2", 10_000),), 8, day=date(2025, 10, 20))
    assert [item.variety for item in lines(book, 2025)] == ["DP 2115", "ST 4990"]


def test_a_variety_on_too_few_fields_is_marked_thin(book: Book) -> None:
    plant(book, "FL-1", "DP 2115")
    a_run(book, "GR-1", (("M-1", "FL-1", 10_000),), 14)
    item = lines(book, 2025)[0]
    assert item.fields < MINIMUM_FIELDS
    assert item.thin
    assert "thin" in variety_table(book, 2025).text()


def test_the_classing_is_weighted_and_carried(book: Book) -> None:
    plant(book, "FL-1", "DP 2115")
    a_run(book, "GR-1", (("M-1", "FL-1", 10_000),), 14)
    item = lines(book, 2025)[0]
    assert item.classed_bales == 14
    assert item.staple == Decimal("35.00")
    assert item.micronaire == Decimal("4.30")
    assert item.loan_value > 0
    assert item.loan_rate > 0


def test_a_run_that_mixed_two_varieties_is_left_out_of_the_classing(
    book: Book,
) -> None:
    plant(book, "FL-1", "DP 2115")
    plant(book, "FL-2", "ST 4990")
    a_run(book, "GR-1", (("M-1", "FL-1", 10_000), ("M-2", "FL-2", 10_000)), 14)
    assert variety_of_run(book, "GR-1") is None
    for item in lines(book, 2025):
        assert item.classed_bales == 0
        assert item.staple == Decimal("0.00")
        assert item.lint_pounds > 0


def test_a_run_on_one_variety_is_attributed_to_it(book: Book) -> None:
    plant(book, "FL-1", "DP 2115")
    a_run(book, "GR-1", (("M-1", "FL-1", 10_000),), 14)
    assert variety_of_run(book, "GR-1") == "DP 2115"


def test_an_unclassed_variety_has_no_loan_value(book: Book) -> None:
    plant(book, "FL-1", "DP 2115")
    a_run(book, "GR-1", (("M-1", "FL-1", 10_000),), 14, classed=False)
    item = lines(book, 2025)[0]
    assert item.classed_bales == 0
    assert item.loan_value == 0
    assert item.loan_rate == Decimal("0.0000")


def test_the_turnout_is_off_the_variety_s_own_cotton(book: Book) -> None:
    plant(book, "FL-1", "DP 2115")
    a_run(book, "GR-1", (("M-1", "FL-1", 20_000),), 14)
    assert lines(book, 2025)[0].turnout == Decimal("0.3430")


def test_the_table_carries_every_column(book: Book) -> None:
    plant(book, "FL-1", "DP 2115")
    a_run(book, "GR-1", (("M-1", "FL-1", 10_000),), 14)
    text = variety_table(book, 2025).text()
    assert "DP 2115" in text
    assert "lint/ac" in text
    assert "mic" in text
