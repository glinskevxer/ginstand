"""The recheck rate, overall and by reason."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ginstand.classing.recheck import request, settle
from ginstand.ginning.press import press
from ginstand.ginning.run import feed, open_run
from ginstand.grades.color import ColorGrade
from ginstand.model.classing import Classing
from ginstand.model.recheck import RecheckOutcome, RecheckReason
from ginstand.report.recheck import by_reason, overall, rate_table, turnaround
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

from .conftest import a_module

OPENED = date(2025, 10, 14)
CLASSED = date(2025, 10, 22)
REQUESTED = date(2025, 10, 27)


def carded(book: Book, count: int = 4) -> None:
    open_run(book, "GR-1", "41207", OPENED)
    receive(book, a_module("M-1", gross_pounds=46_140, tare_pounds=26_140))
    feed(book, "GR-1", "M-1", OPENED)
    for _ in range(count):
        bale = press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
        book.cards.add(
            Classing(
                tag=bale.tag,
                classed=CLASSED,
                color=ColorGrade(31),
                leaf=3,
                staple=35,
                micronaire=Decimal("4.3"),
                strength=Decimal("29.4"),
                uniformity=Decimal("81.2"),
            )
        )


def test_a_book_with_no_rechecks_says_so(book: Book) -> None:
    assert rate_table(book).render()[-1] == "no rechecks have been asked for"
    assert overall(book).asked == 0
    assert overall(book).success == Decimal("0.00")


def test_the_overall_rate_counts_every_outcome(book: Book) -> None:
    carded(book)
    for sequence, outcome in (
        (1, RecheckOutcome.CHANGED),
        (2, RecheckOutcome.UNCHANGED),
        (3, RecheckOutcome.REFUSED),
    ):
        tag = f"2541207{sequence:05d}"
        request(book, tag, RecheckReason.COLOUR, REQUESTED)
        settle(book, tag, date(2025, 11, 3), outcome)
    request(book, "254120700004", RecheckReason.LEAF, REQUESTED)

    rate = overall(book)
    assert rate.asked == 4
    assert rate.changed == 1
    assert rate.unchanged == 1
    assert rate.refused == 1
    assert rate.still_out == 1
    assert rate.answered == 3


def test_the_moved_rate_is_over_the_ones_the_office_read(book: Book) -> None:
    carded(book)
    for sequence, outcome in (
        (1, RecheckOutcome.CHANGED),
        (2, RecheckOutcome.UNCHANGED),
        (3, RecheckOutcome.REFUSED),
    ):
        tag = f"2541207{sequence:05d}"
        request(book, tag, RecheckReason.COLOUR, REQUESTED)
        settle(book, tag, date(2025, 11, 3), outcome)
    assert overall(book).success == Decimal("50.00")


def test_a_refusal_is_not_counted_against_the_gin(book: Book) -> None:
    carded(book, 2)
    for sequence in (1, 2):
        tag = f"2541207{sequence:05d}"
        request(book, tag, RecheckReason.COLOUR, REQUESTED)
    settle(book, "254120700001", date(2025, 11, 3), RecheckOutcome.CHANGED)
    settle(book, "254120700002", date(2025, 11, 3), RecheckOutcome.REFUSED)
    assert overall(book).success == Decimal("100.00")


def test_the_split_by_reason_separates_them(book: Book) -> None:
    carded(book)
    request(book, "254120700001", RecheckReason.COLOUR, REQUESTED)
    settle(book, "254120700001", date(2025, 11, 3), RecheckOutcome.CHANGED)
    request(book, "254120700002", RecheckReason.MICRONAIRE, REQUESTED)
    settle(book, "254120700002", date(2025, 11, 3), RecheckOutcome.UNCHANGED)
    split = by_reason(book)
    assert set(split) == {RecheckReason.COLOUR, RecheckReason.MICRONAIRE}
    assert split[RecheckReason.COLOUR].success == Decimal("100.00")
    assert split[RecheckReason.MICRONAIRE].success == Decimal("0.00")


def test_a_reason_nobody_used_is_left_off(book: Book) -> None:
    carded(book)
    request(book, "254120700001", RecheckReason.COLOUR, REQUESTED)
    assert RecheckReason.STAPLE not in by_reason(book)


def test_the_table_totals_every_reason(book: Book) -> None:
    carded(book)
    request(book, "254120700001", RecheckReason.COLOUR, REQUESTED)
    request(book, "254120700002", RecheckReason.LEAF, REQUESTED)
    text = rate_table(book).text()
    assert "colour" in text
    assert "leaf" in text
    assert "Recheck outcomes" in text


def test_the_turnaround_is_the_mean_over_answered_requests(book: Book) -> None:
    carded(book)
    request(book, "254120700001", RecheckReason.COLOUR, REQUESTED)
    settle(book, "254120700001", date(2025, 11, 3), RecheckOutcome.CHANGED)
    request(book, "254120700002", RecheckReason.LEAF, REQUESTED)
    settle(book, "254120700002", date(2025, 11, 9), RecheckOutcome.UNCHANGED)
    assert turnaround(book, date(2025, 11, 20)) == Decimal("10.0")


def test_a_book_with_nothing_answered_has_no_turnaround(book: Book) -> None:
    carded(book)
    request(book, "254120700001", RecheckReason.COLOUR, REQUESTED)
    assert turnaround(book, date(2025, 11, 3)) == Decimal("0.0")


def test_the_rate_line_reads_as_one_sentence(book: Book) -> None:
    carded(book)
    request(book, "254120700001", RecheckReason.COLOUR, REQUESTED)
    settle(book, "254120700001", date(2025, 11, 3), RecheckOutcome.CHANGED)
    assert overall(book).line == "1 asked, 1 changed, 0 unchanged, 0 refused, 0 out  (100.00%)"
