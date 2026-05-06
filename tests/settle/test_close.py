"""Closing a crop year pays out the fractions of a bale that are left."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import NotFoundError, StateError
from ginstand.ginning.run import close_run
from ginstand.grades.color import ColorGrade
from ginstand.model.account import EntryKind
from ginstand.model.classing import Classing
from ginstand.settle.close import (
    close,
    closing_for,
    is_closed,
    mean_rate,
    require_closing,
    summary,
    unfinished,
)
from ginstand.store.book import Book

from .conftest import OPENED, gin_a_run, press_a_run

CLOSED = date(2026, 3, 1)


def class_all(book: Book) -> None:
    for bale in book.bales.list_all():
        book.cards.add(
            Classing(
                tag=bale.tag,
                classed=date(2025, 10, 22),
                color=ColorGrade(31),
                leaf=3,
                staple=34,
                micronaire=Decimal("4.5"),
                strength=Decimal("27.0"),
                uniformity=Decimal("81.0"),
            )
        )


def test_a_crop_year_starts_open(book: Book) -> None:
    gin_a_run(book)
    assert not is_closed(book, 2025)
    assert closing_for(book, 2025) is None
    with pytest.raises(NotFoundError, match="no crop year close with reference 2025"):
        require_closing(book, 2025)


def test_a_run_still_open_stops_the_close(book: Book) -> None:
    press_a_run(book)
    assert unfinished(book, 2025) == ("gin run GR-1 is still open",)
    with pytest.raises(StateError, match="is still open"):
        close(book, 2025, CLOSED)


def test_a_run_never_allocated_stops_the_close(book: Book) -> None:
    press_a_run(book)
    close_run(book, "GR-1", OPENED)
    assert unfinished(book, 2025) == ("gin run GR-1 has not been allocated",)
    with pytest.raises(StateError, match="has not been allocated"):
        close(book, 2025, CLOSED)


def test_a_finished_crop_year_closes(book: Book) -> None:
    gin_a_run(book, bales=7)
    class_all(book)
    closing, posted = close(book, 2025, CLOSED)
    assert is_closed(book, 2025)
    assert closing.crop_year == 2025
    assert closing.bale_weight == 490
    assert closing.rate > 0
    assert require_closing(book, 2025) == closing
    assert posted


def test_closing_twice_is_refused(book: Book) -> None:
    gin_a_run(book)
    class_all(book)
    close(book, 2025, CLOSED)
    with pytest.raises(StateError, match="was already closed"):
        close(book, 2025, CLOSED)


def test_a_crop_year_with_no_bales_cannot_close(book: Book) -> None:
    press_a_run(book, bales=0)
    close_run(book, "GR-1", OPENED)
    with pytest.raises(StateError, match="pressed no bales"):
        close(book, 2025, CLOSED)


def test_the_carries_are_paid_and_zeroed(book: Book) -> None:
    gin_a_run(book, bales=7)
    class_all(book)
    before = {p: c for p, c in book.allocations.carries(2025).items() if c != 0}
    assert before
    _, posted = close(book, 2025, CLOSED)
    assert {entry.producer for entry in posted} == set(before)
    assert all(c == 0 for c in book.allocations.carries(2025).values())


def test_the_paid_carries_land_on_the_account(book: Book) -> None:
    gin_a_run(book, bales=7)
    class_all(book)
    _, posted = close(book, 2025, CLOSED)
    for entry in posted:
        assert entry.kind is EntryKind.ADJUSTMENT
        assert "of a bale carried at close" in entry.note
        assert book.accounts.balance(entry.producer, 2025) == entry.amount


def test_a_producer_owed_a_fraction_is_paid_and_the_other_is_charged(
    book: Book,
) -> None:
    gin_a_run(book, bales=7)
    class_all(book)
    _, posted = close(book, 2025, CLOSED)
    amounts = [entry.amount for entry in posted]
    assert any(amount > 0 for amount in amounts)
    assert any(amount < 0 for amount in amounts)


def test_the_rate_is_the_season_s_own(book: Book) -> None:
    gin_a_run(book)
    class_all(book)
    assert mean_rate(book, 2025) == Decimal("52.0000")


def test_an_unclassed_crop_year_has_no_rate(book: Book) -> None:
    gin_a_run(book)
    assert mean_rate(book, 2025) == Decimal("0.0000")


def test_a_run_that_divides_exactly_leaves_no_carry_to_pay(book: Book) -> None:
    gin_a_run(book, bales=8)
    assert all(carry == 0 for carry in book.allocations.carries(2025).values())
    _, posted = close(book, 2025, CLOSED)
    assert posted == ()


def test_a_carry_with_nothing_classed_is_worth_nothing(book: Book) -> None:
    gin_a_run(book, bales=7)
    assert any(carry != 0 for carry in book.allocations.carries(2025).values())
    _, posted = close(book, 2025, CLOSED)
    assert posted == ()


def test_the_summary_says_what_is_stopping_it(book: Book) -> None:
    press_a_run(book)
    assert summary(book, 2025) == ("not ready: gin run GR-1 is still open",)


def test_the_summary_prices_the_carries_before_closing(book: Book) -> None:
    gin_a_run(book, bales=7)
    class_all(book)
    lines = summary(book, 2025)
    assert lines[0] == "crop year 2025 is ready to close"
    assert any("carries" in line for line in lines)


def test_the_summary_reads_back_the_close_afterwards(book: Book) -> None:
    gin_a_run(book)
    class_all(book)
    close(book, 2025, CLOSED)
    assert summary(book, 2025)[0].startswith("crop year 2025 closed 2026-03-01")
