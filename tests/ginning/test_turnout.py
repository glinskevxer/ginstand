"""Turnout is final only once the run is closed, and the two figures differ."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import StateError
from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.ginning.turnout import (
    HIGH_TURNOUT,
    LOW_TURNOUT,
    turnout_for,
    turnout_so_far,
)
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

from .conftest import GIN, a_module

OPENED = date(2025, 10, 14)


def run_with(book: Book, seed_cotton: int, bales: int, net: int = 490) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    receive(book, a_module("M-1", gross_pounds=26_140 + seed_cotton, tare_pounds=26_140))
    feed(book, "GR-1", "M-1", OPENED)
    for _ in range(bales):
        press(book, "GR-1", OPENED, net + 22, 22, Decimal("6.8"))


def test_turnout_is_lint_over_seed_cotton(book: Book) -> None:
    run_with(book, seed_cotton=20_000, bales=14)
    close_run(book, "GR-1", OPENED)
    figure = turnout_for(book, "GR-1")
    assert figure.seed_cotton_pounds == 20_000
    assert figure.lint_pounds == 14 * 490
    assert figure.lint_turnout == Decimal("0.3430")
    assert figure.final


def test_an_open_run_has_no_final_turnout(book: Book) -> None:
    run_with(book, seed_cotton=20_000, bales=14)
    with pytest.raises(StateError, match="still open, so its turnout is not final"):
        turnout_for(book, "GR-1")


def test_the_figure_so_far_is_available_while_the_run_is_open(book: Book) -> None:
    run_with(book, seed_cotton=20_000, bales=7)
    figure = turnout_so_far(book, "GR-1")
    assert not figure.final
    assert figure.lint_turnout == Decimal("0.1715")
    assert figure.line.endswith("(so far)  LOW")


def test_a_run_with_no_seed_cotton_has_no_turnout_at_all(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    with pytest.raises(StateError, match="has no seed cotton in it"):
        turnout_so_far(book, "GR-1")


def test_a_turnout_in_the_band_is_not_flagged(book: Book) -> None:
    run_with(book, seed_cotton=20_000, bales=14)
    close_run(book, "GR-1", OPENED)
    figure = turnout_for(book, "GR-1")
    assert figure.in_band
    assert not figure.low
    assert not figure.high
    assert figure.line == "GR-1  14 bales  0.3430 turnout (final)"


def test_a_low_turnout_points_at_the_cotton(book: Book) -> None:
    run_with(book, seed_cotton=20_000, bales=11)
    close_run(book, "GR-1", OPENED)
    figure = turnout_for(book, "GR-1")
    assert figure.lint_turnout < LOW_TURNOUT
    assert figure.low
    assert figure.line.endswith("LOW")


def test_a_high_turnout_points_at_the_scale(book: Book) -> None:
    run_with(book, seed_cotton=20_000, bales=19)
    close_run(book, "GR-1", OPENED)
    figure = turnout_for(book, "GR-1")
    assert figure.lint_turnout > HIGH_TURNOUT
    assert figure.high
    assert figure.line.endswith("HIGH")


def test_the_per_bale_figures_round_to_the_pound(book: Book) -> None:
    run_with(book, seed_cotton=20_000, bales=14)
    close_run(book, "GR-1", OPENED)
    figure = turnout_for(book, "GR-1")
    assert figure.lint_per_bale == 490
    assert figure.seed_cotton_per_bale == 1_429


def test_a_run_with_no_bales_has_no_per_bale_figure(book: Book) -> None:
    open_run(book, "GR-1", GIN, OPENED)
    receive(book, a_module("M-1"))
    feed(book, "GR-1", "M-1", OPENED)
    figure = turnout_so_far(book, "GR-1")
    assert figure.bales == 0
    with pytest.raises(StateError, match="has pressed no bales"):
        assert figure.lint_per_bale
    with pytest.raises(StateError, match="has pressed no bales"):
        assert figure.seed_cotton_per_bale
