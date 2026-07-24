"""Walking a plastic note back to the modules that could have caused it."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ginstand.ginning.press import press
from ginstand.ginning.run import close_run, feed, open_run
from ginstand.grades.color import ColorGrade
from ginstand.grades.matter import Extraneous, ExtraneousKind, ExtraneousLevel
from ginstand.model.classing import Classing
from ginstand.model.module import ModuleKind, WrapKind
from ginstand.report.plastic import (
    fields_behind,
    for_run,
    plastic_table,
    season,
    suspects,
)
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

from .conftest import a_module

OPENED = date(2025, 10, 14)


def a_run(
    book: Book,
    ref: str,
    feeds: tuple[tuple[str, str, bool], ...],
    notes: tuple[tuple[int, ExtraneousLevel | None], ...],
    bales: int = 4,
    day: date = OPENED,
) -> None:
    open_run(book, ref, "41207", day)
    for tag, field_ref, film in feeds:
        receive(
            book,
            a_module(
                tag,
                field=field_ref,
                gross_pounds=46_140,
                tare_pounds=26_140,
                kind=ModuleKind.ROUND if film else ModuleKind.RECTANGULAR,
                wrap=WrapKind.FILM if film else WrapKind.TARP,
            ),
        )
        feed(book, ref, tag, day)
    flagged = dict(notes)
    for index in range(bales):
        bale = press(book, ref, day, 512, 22, Decimal("6.8"))
        level = flagged.get(index)
        extraneous = (Extraneous(ExtraneousKind.PLASTIC, level),) if level is not None else ()
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
                extraneous=extraneous,
            )
        )
    close_run(book, ref, day)


def test_a_run_with_no_plastic_is_clean(book: Book) -> None:
    a_run(book, "GR-1", (("M-1", "FL-9", False),), ())
    item = for_run(book, "GR-1")
    assert item.flagged == 0
    assert item.rate == Decimal("0.00")
    assert not item.unexplained


def test_a_film_module_makes_a_suspect_list(book: Book) -> None:
    a_run(
        book, "GR-1", (("M-1", "FL-9", True), ("M-2", "FL-5", False)), ((0, ExtraneousLevel.LIGHT),)
    )
    item = for_run(book, "GR-1")
    assert item.had_film
    assert item.film_modules == ("M-1",)
    assert item.other_modules == ("M-2",)
    assert not item.unexplained


def test_plastic_with_no_film_in_the_run_is_unexplained(book: Book) -> None:
    a_run(book, "GR-1", (("M-1", "FL-9", False),), ((0, ExtraneousLevel.HEAVY),))
    item = for_run(book, "GR-1")
    assert not item.had_film
    assert item.unexplained
    assert "UNEXPLAINED" in item.line


def test_film_with_no_plastic_note_is_not_a_finding(book: Book) -> None:
    a_run(book, "GR-1", (("M-1", "FL-9", True),), ())
    item = for_run(book, "GR-1")
    assert item.had_film
    assert not item.unexplained
    assert season(book, 2025) == ()


def test_the_rate_is_over_the_run_s_own_bales(book: Book) -> None:
    a_run(
        book,
        "GR-1",
        (("M-1", "FL-9", True),),
        ((0, ExtraneousLevel.LIGHT), (1, ExtraneousLevel.HEAVY)),
        bales=4,
    )
    item = for_run(book, "GR-1")
    assert item.flagged == 2
    assert item.heavy == 1
    assert item.rate == Decimal("50.00")


def test_the_season_lists_the_worst_run_first(book: Book) -> None:
    a_run(book, "GR-1", (("M-1", "FL-9", True),), ((0, ExtraneousLevel.LIGHT),), bales=4)
    a_run(
        book,
        "GR-2",
        (("M-2", "FL-5", True),),
        ((0, ExtraneousLevel.LIGHT), (1, ExtraneousLevel.LIGHT)),
        bales=4,
        day=date(2025, 10, 20),
    )
    assert [item.run for item in season(book, 2025)] == ["GR-2", "GR-1"]


def test_a_run_with_no_plastic_is_left_off_the_season(book: Book) -> None:
    a_run(book, "GR-1", (("M-1", "FL-9", True),), ())
    a_run(
        book,
        "GR-2",
        (("M-2", "FL-5", True),),
        ((0, ExtraneousLevel.LIGHT),),
        day=date(2025, 10, 20),
    )
    assert [item.run for item in season(book, 2025)] == ["GR-2"]


def test_the_suspects_for_a_bale_are_its_run_s_film_modules(book: Book) -> None:
    a_run(
        book, "GR-1", (("M-1", "FL-9", True), ("M-2", "FL-5", False)), ((0, ExtraneousLevel.HEAVY),)
    )
    assert suspects(book, "254120700001") == ("M-1",)


def test_a_bale_off_a_run_with_no_film_has_no_suspects(book: Book) -> None:
    a_run(book, "GR-1", (("M-1", "FL-9", False),), ((0, ExtraneousLevel.HEAVY),))
    assert suspects(book, "254120700001") == ()


def test_the_fields_behind_the_film_are_named(book: Book) -> None:
    a_run(
        book, "GR-1", (("M-1", "FL-9", True), ("M-2", "FL-5", True)), ((0, ExtraneousLevel.LIGHT),)
    )
    assert fields_behind(book, "GR-1") == ("FL-5", "FL-9")


def test_a_run_with_no_film_has_no_fields_behind_it(book: Book) -> None:
    a_run(book, "GR-1", (("M-1", "FL-9", False),), ((0, ExtraneousLevel.LIGHT),))
    assert fields_behind(book, "GR-1") == ()


def test_a_clean_crop_year_says_so(book: Book) -> None:
    a_run(book, "GR-1", (("M-1", "FL-9", True),), ())
    assert plastic_table(book, 2025).render()[-1] == "no bale came back with a plastic note"


def test_the_table_carries_the_fields_and_the_note(book: Book) -> None:
    a_run(book, "GR-1", (("M-1", "FL-9", True),), ((0, ExtraneousLevel.HEAVY),))
    text = plastic_table(book, 2025).text()
    assert "GR-1" in text
    assert "FL-9" in text


def test_a_run_that_pressed_nothing_is_left_off(book: Book) -> None:
    """This report wants the pressed set, because a plastic note is on a bale."""
    a_run(book, "GR-1", (("M-1", "FL-9", True),), (), bales=0)
    assert season(book, 2025) == ()
