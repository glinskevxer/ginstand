"""A run's statements, worked out before any of them is written."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from ginstand.charges.published import seed_price_for, tariff_for
from ginstand.errors import StateError
from ginstand.ginning.allocate import allocate
from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.report.batch import build, file_name, write
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

from .conftest import a_module

OPENED = date(2025, 10, 14)
ISSUED = date(2025, 11, 3)
TARIFF = tariff_for(2025)
SEED = seed_price_for(2025)


@pytest.fixture
def ginned(book: Book) -> Book:
    open_run(book, "GR-1", "41207", OPENED)
    for tag, field_ref, net in (("M-1", "FL-9", 20_000), ("M-2", "FL-5", 10_000)):
        receive(
            book,
            a_module(tag, field=field_ref, gross_pounds=26_140 + net, tare_pounds=26_140),
        )
        feed(book, "GR-1", tag, OPENED)
    for _ in range(9):
        press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
    close_run(book, "GR-1", OPENED)
    allocate(book, "GR-1", OPENED)
    return book


def test_a_statement_is_named_for_its_run_and_producer() -> None:
    assert file_name("gr-1", "p-12") == "GR-1-P-12.txt"


def test_a_run_nobody_is_on_has_no_statements(book: Book) -> None:
    open_run(book, "GR-1", "41207", OPENED)
    with pytest.raises(StateError, match="nobody has cotton on gin run GR-1"):
        build(book, "GR-1", TARIFF, SEED, ISSUED)


def test_every_producer_on_the_run_gets_a_page(ginned: Book) -> None:
    pages = build(ginned, "GR-1", TARIFF, SEED, ISSUED)
    assert set(pages) == {"P-12", "P-40"}
    for producer, lines in pages.items():
        assert lines[0].startswith(f"Gin run GR-1   {producer}")


def test_the_pages_are_built_and_nothing_is_written(ginned: Book, tmp_path: Path) -> None:
    build(ginned, "GR-1", TARIFF, SEED, ISSUED)
    assert list(tmp_path.iterdir()) == []


def test_writing_makes_one_file_per_producer(ginned: Book, tmp_path: Path) -> None:
    printed = write(ginned, "GR-1", TARIFF, SEED, ISSUED, tmp_path / "out")
    assert len(printed) == 2
    for item in printed:
        assert item.path.is_file()
        assert item.lines > 5
        assert item.path.read_text().startswith("Gin run GR-1")


def test_the_folder_is_made_if_it_is_not_there(ginned: Book, tmp_path: Path) -> None:
    folder = tmp_path / "deep" / "out"
    write(ginned, "GR-1", TARIFF, SEED, ISSUED, folder)
    assert folder.is_dir()
    assert len(list(folder.iterdir())) == 2


def test_a_file_where_the_folder_should_be_is_refused(ginned: Book, tmp_path: Path) -> None:
    blocker = tmp_path / "out"
    blocker.write_text("in the way")
    with pytest.raises(StateError, match="is a file, not a folder"):
        write(ginned, "GR-1", TARIFF, SEED, ISSUED, blocker)


def test_a_run_that_cannot_be_settled_writes_nothing(book: Book, tmp_path: Path) -> None:
    open_run(book, "GR-1", "41207", OPENED)
    receive(book, a_module("M-1", gross_pounds=46_140, tare_pounds=26_140))
    feed(book, "GR-1", "M-1", OPENED)
    press(book, "GR-1", OPENED, 512, 22, Decimal("6.8"))
    folder = tmp_path / "out"
    with pytest.raises(StateError):
        write(book, "GR-1", TARIFF, SEED, ISSUED, folder)
    assert not folder.exists()


def test_the_printed_line_names_the_file(ginned: Book, tmp_path: Path) -> None:
    printed = write(ginned, "GR-1", TARIFF, SEED, ISSUED, tmp_path / "out")
    assert printed[0].line.endswith(".txt")
    assert printed[0].producer in printed[0].line
