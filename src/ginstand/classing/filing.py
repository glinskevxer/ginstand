"""Filing a read classing file into the book.

Reading the file and filing it are separate on purpose. A file reads the same
way whatever is in the book, and filing it is where the book's own objections
come up: a tag nobody pressed, a bale that already has a card, a card dated
before the bale existed.

Filing is all or nothing per card, never per file. A file with two bad records
and three hundred good ones files the three hundred, and the office chases the
two. Refusing the file would mean nothing gets filed until somebody at the
classing office is reachable, which on a Friday afternoon is never.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from ginstand.classing.ingest import Reading
from ginstand.classing.recheck import settle_from_card
from ginstand.errors import GinstandError
from ginstand.model.classing import Classing
from ginstand.store.book import Book


@dataclass(frozen=True, slots=True)
class Rejected:
    """A card that read cleanly and the book would not take."""

    tag: str
    reason: str


@dataclass(frozen=True, slots=True)
class Filing:
    """What happened when a file was filed."""

    filed: tuple[str, ...]
    replaced: tuple[str, ...]
    rejected: tuple[Rejected, ...]

    @property
    def clean(self) -> bool:
        """Whether every card went in."""
        return not self.rejected

    @property
    def summary(self) -> str:
        """The line the office reads after a filing."""
        return (
            f"{len(self.filed)} filed, {len(self.replaced)} replaced, {len(self.rejected)} rejected"
        )


def check(book: Book, card: Classing, recheck: bool) -> str:
    """Why the book would not take this card, or an empty string."""
    bale = book.bales.find(card.tag)
    if bale is None:
        return "no bale in the book carries this tag"
    if card.classed < bale.pressed:
        return (
            f"the card is dated {card.classed.isoformat()} and the bale was pressed "
            f"on {bale.pressed.isoformat()}"
        )
    if book.cards.exists(card.tag) and not recheck:
        return "the bale already has a card, and this file is not a recheck"
    return ""


def file_card(book: Book, card: Classing, recheck: bool = False) -> str:
    """File one card. Returns "filed", "replaced", or the reason it was not taken.

    Replacing a card closes the bale's open recheck request, if it has one, and
    the outcome is worked out by comparing the two cards rather than asserted.
    """
    reason = check(book, card, recheck)
    if reason:
        return reason
    standing = book.cards.find(card.tag)
    if standing is not None:
        book.cards.replace(card)
        settle_from_card(book, standing, card, card.classed)
        return "replaced"
    book.cards.add(card)
    return "filed"


def file_reading(book: Book, reading: Reading, recheck: bool = False) -> Filing:
    """File every card a read produced, keeping the ones the book refused."""
    filed: list[str] = []
    replaced: list[str] = []
    rejected: list[Rejected] = []
    for card in reading.cards:
        try:
            outcome = file_card(book, card, recheck)
        except GinstandError as exc:
            rejected.append(Rejected(tag=card.tag, reason=str(exc)))
            continue
        if outcome == "filed":
            filed.append(card.tag)
        elif outcome == "replaced":
            replaced.append(card.tag)
        else:
            rejected.append(Rejected(tag=card.tag, reason=outcome))
    return Filing(filed=tuple(filed), replaced=tuple(replaced), rejected=tuple(rejected))


def outstanding(book: Book) -> tuple[str, ...]:
    """Every bale in the book still waiting on a card."""
    return book.cards.unclassed_tags()


def rechecks_closed_by(book: Book, on: date) -> int:
    """How many recheck requests a day's filing answered."""
    return len(book.rechecks.settled_between(on, on))
