"""Where a module is standing, and what that costs the loader.

The yard is rows, and a row is worked from one end. A module in the middle of a
row cannot be got at without moving the ones in front of it, so the order the
office would like to gin in and the order the yard can actually feed are not the
same order, and the difference is real money in loader hours.

So the queue can be asked for twice. The plain one is the order the cotton
should gin in, worst first, and it ignores the yard entirely. The row order
takes that queue and works each row through from its open end, which means a
module deep in a row waits for the ones in front of it however bad it is.

Neither is right on its own. The yard manager reads both and decides, which is
what the two functions are for: this package does not have an opinion about
whether a spoiling module is worth an hour of loader time.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date

from ginstand.errors import NotFoundError, StateError
from ginstand.ids import reference, row_name
from ginstand.store.book import Book
from ginstand.store.sqlite import as_date
from ginstand.yard.order import queue


@dataclass(frozen=True, slots=True)
class Place:
    """Where one module is standing."""

    module: str
    row: str
    position: int
    placed: date

    @property
    def line(self) -> str:
        """The line the yard map prints."""
        return f"{self.row}-{self.position:02d}  {self.module}"


def _place_from(row: sqlite3.Row) -> Place:
    return Place(
        module=str(row["module"]),
        row=str(row["yard_row"]),
        position=int(row["position"]),
        placed=as_date(row["placed"]),
    )


def place_of(book: Book, tag: str) -> Place | None:
    """Where a module is standing, or None if nobody wrote it down."""
    row = book.connection.execute(
        "SELECT * FROM yard_place WHERE module = ?",
        (reference(tag, "module tag"),),
    ).fetchone()
    return None if row is None else _place_from(row)


def next_position(book: Book, yard_row: str) -> int:
    """The position the next module put in a row will take."""
    row = book.connection.execute(
        "SELECT coalesce(max(position), 0) AS last FROM yard_place WHERE yard_row = ?",
        (row_name(yard_row),),
    ).fetchone()
    return int(row["last"]) + 1


def put(book: Book, tag: str, yard_row: str, on: date) -> Place:
    """Stand a module at the open end of a row."""
    module = book.modules.get(tag)
    if book.runs.run_of(module.tag) is not None:
        raise StateError(f"module {module.tag} has already been ginned")
    if place_of(book, module.tag) is not None:
        raise StateError(f"module {module.tag} is already standing in the yard")
    if on < module.received:
        raise StateError(
            f"{on.isoformat()} is before module {module.tag} was received "
            f"on {module.received.isoformat()}"
        )
    row_ref = row_name(yard_row)
    position = next_position(book, row_ref)
    book.connection.execute(
        "INSERT INTO yard_place (module, yard_row, position, placed) VALUES (?, ?, ?, ?)",
        (module.tag, row_ref, position, on.isoformat()),
    )
    return Place(module=module.tag, row=row_ref, position=position, placed=on)


def lift(book: Book, tag: str) -> Place:
    """Take a module out of the yard, because it has gone to the stands."""
    found = place_of(book, tag)
    if found is None:
        raise NotFoundError("yard place", reference(tag, "module tag"))
    book.connection.execute("DELETE FROM yard_place WHERE module = ?", (found.module,))
    return found


def row_listing(book: Book, yard_row: str) -> tuple[Place, ...]:
    """Every module in a row, from the closed end to the open one."""
    rows = book.connection.execute(
        "SELECT * FROM yard_place WHERE yard_row = ? ORDER BY position",
        (row_name(yard_row),),
    ).fetchall()
    return tuple(_place_from(row) for row in rows)


def rows(book: Book) -> tuple[str, ...]:
    """Every row with something in it, in name order."""
    found = book.connection.execute(
        "SELECT DISTINCT yard_row FROM yard_place ORDER BY yard_row"
    ).fetchall()
    return tuple(str(row["yard_row"]) for row in found)


def buried(book: Book, tag: str) -> tuple[str, ...]:
    """The modules standing in front of one, which have to move first."""
    found = place_of(book, tag)
    if found is None:
        raise NotFoundError("yard place", reference(tag, "module tag"))
    return tuple(
        item.module for item in row_listing(book, found.row) if item.position > found.position
    )


def row_order(book: Book, tags: tuple[str, ...], on: date) -> tuple[str, ...]:
    """The queue reordered so each row is worked from its open end.

    A module with no place recorded is treated as reachable, because a yard that
    has not been mapped is not a yard that should stop the gin.
    """
    wanted = list(queue(book, tags, on))
    ordered: list[str] = []
    while wanted:
        for tag in list(wanted):
            blockers = (
                [item for item in buried(book, tag) if item in wanted]
                if place_of(book, tag)
                else []
            )
            if not blockers:
                ordered.append(tag)
                wanted.remove(tag)
                break
        else:  # pragma: no cover - a row cannot block itself in a cycle
            ordered.extend(wanted)
            break
    return tuple(ordered)


def digging(book: Book, tags: tuple[str, ...], on: date) -> int:
    """How many modules have to be shifted to gin the queue in its own order.

    This is the number the yard manager is actually deciding about. Zero means
    the two orders agree and there is nothing to argue about.
    """
    plain = queue(book, tags, on)
    by_row = row_order(book, tags, on)
    return sum(1 for left, right in zip(plain, by_row, strict=True) if left != right)
