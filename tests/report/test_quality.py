"""Averages are weighted by bale weight, because that is the number that survives a meeting."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.classing.color import ColorGrade
from ginstand.classing.matter import Extraneous, ExtraneousKind, ExtraneousLevel
from ginstand.errors import StateError
from ginstand.ginning.press import press
from ginstand.ginning.run import feed, open_run
from ginstand.model.classing import Classing
from ginstand.report.quality import (
    averages,
    colour_spread,
    contamination,
    off_schedule,
    staple_spread,
    summary,
)
from ginstand.store.book import Book
from ginstand.yard.receiving import receive

from .conftest import a_module

OPENED = date(2025, 10, 14)


def press_bales(book: Book, weights: tuple[int, ...]) -> tuple[str, ...]:
    open_run(book, "GR-1", "41207", OPENED)
    receive(book, a_module("M-1", gross_pounds=76_140, tare_pounds=26_140))
    feed(book, "GR-1", "M-1", OPENED)
    tags = []
    for net in weights:
        tags.append(press(book, "GR-1", OPENED, net + 22, 22, Decimal("6.8")).tag)
    return tuple(tags)


def card(tag: str, **changes: object) -> Classing:
    fields: dict[str, object] = {
        "tag": tag,
        "classed": date(2025, 10, 22),
        "color": ColorGrade(31),
        "leaf": 3,
        "staple": 35,
        "micronaire": Decimal("4.3"),
        "strength": Decimal("29.4"),
        "uniformity": Decimal("81.2"),
    }
    fields.update(changes)
    return Classing(**fields)  # type: ignore[arg-type]


def test_a_crop_year_with_nothing_classed_has_no_averages(book: Book) -> None:
    press_bales(book, (490,))
    with pytest.raises(StateError, match="no bale in crop year 2025 has been classed"):
        averages(book, 2025)


def test_the_averages_are_weighted_by_bale_weight(book: Book) -> None:
    tags = press_bales(book, (700, 300))
    book.cards.add(card(tags[0], micronaire=Decimal("5.0")))
    book.cards.add(card(tags[1], micronaire=Decimal("3.0")))
    figures = averages(book, 2025)
    assert figures.bales == 2
    assert figures.pounds == 1000
    assert figures.micronaire == Decimal("4.40")


def test_an_unweighted_mean_would_be_a_different_number(book: Book) -> None:
    tags = press_bales(book, (700, 300))
    book.cards.add(card(tags[0], micronaire=Decimal("5.0")))
    book.cards.add(card(tags[1], micronaire=Decimal("3.0")))
    assert averages(book, 2025).micronaire != Decimal("4.00")


def test_the_averages_cover_every_reading_on_the_card(book: Book) -> None:
    tags = press_bales(book, (490,))
    book.cards.add(card(tags[0]))
    figures = averages(book, 2025)
    assert figures.staple == Decimal("35.00")
    assert figures.leaf == Decimal("3.00")
    assert figures.strength == Decimal("29.40")
    assert figures.uniformity == Decimal("81.20")


def test_the_colour_spread_counts_and_shares(book: Book) -> None:
    tags = press_bales(book, (490, 490, 490))
    book.cards.add(card(tags[0], color=ColorGrade(31)))
    book.cards.add(card(tags[1], color=ColorGrade(31)))
    book.cards.add(card(tags[2], color=ColorGrade(41)))
    text = colour_spread(book, 2025).text()
    assert "Middling White" in text
    assert "66.7%" in text
    assert "33.3%" in text


def test_an_unclassed_crop_year_says_so_on_the_spreads(book: Book) -> None:
    press_bales(book, (490,))
    assert colour_spread(book, 2025).render()[-1] == "nothing has been classed"
    assert staple_spread(book, 2025).render()[-1] == "nothing has been classed"


def test_the_staple_spread_lists_shortest_first(book: Book) -> None:
    tags = press_bales(book, (490, 490))
    book.cards.add(card(tags[0], staple=37))
    book.cards.add(card(tags[1], staple=34))
    lines = staple_spread(book, 2025).render()
    assert lines[4].startswith("34")
    assert lines[5].startswith("37")


def test_the_off_schedule_list_says_whose_rule_applied(book: Book) -> None:
    tags = press_bales(book, (490, 490, 490))
    book.cards.add(card(tags[0]))
    book.cards.add(card(tags[1], leaf=8))
    book.cards.add(
        card(tags[2], extraneous=(Extraneous(ExtraneousKind.PLASTIC, ExtraneousLevel.HEAVY),))
    )
    text = off_schedule(book, 2025).text()
    assert "leaf below grade" in text
    assert "heavy plastic" in text
    assert "the office" in text
    assert "ours" in text


def test_a_clean_crop_year_has_nothing_off_the_schedule(book: Book) -> None:
    tags = press_bales(book, (490,))
    book.cards.add(card(tags[0]))
    assert off_schedule(book, 2025).render()[-1] == "every classed bale is on the schedule"


def test_contamination_counts_the_notes(book: Book) -> None:
    tags = press_bales(book, (490, 490))
    book.cards.add(card(tags[0], extraneous=(Extraneous(ExtraneousKind.BARK),)))
    book.cards.add(
        card(tags[1], extraneous=(Extraneous(ExtraneousKind.PLASTIC, ExtraneousLevel.HEAVY),))
    )
    text = contamination(book, 2025).text()
    assert "BK1" in text
    assert "PL2" in text
    assert "plastic" in text


def test_a_clean_crop_year_notes_no_extraneous_matter(book: Book) -> None:
    tags = press_bales(book, (490,))
    book.cards.add(card(tags[0]))
    assert contamination(book, 2025).render()[-1] == "no extraneous matter was noted"


def test_the_summary_heads_the_report_with_the_averages(book: Book) -> None:
    tags = press_bales(book, (490, 490))
    book.cards.add(card(tags[0]))
    book.cards.add(card(tags[1], leaf=8))
    lines = summary(book, 2025)
    assert lines[0].startswith("Crop year 2025: 2 bales classed")
    assert "mic 4.30" in lines[1]
    assert "off the schedule: 1 leaf below grade" in lines[2]


def test_a_clean_summary_has_no_off_schedule_line(book: Book) -> None:
    tags = press_bales(book, (490,))
    book.cards.add(card(tags[0]))
    assert len(summary(book, 2025)) == 2
