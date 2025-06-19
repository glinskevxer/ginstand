"""Cottonseed: the other thing that comes out of a gin run.

Seed is about half the weight of what goes in and it is worth real money, so it
is not a by-product in the accounting sense even if it is one in the machine.
The gin usually buys it, and what it pays is a credit on the producer's
settlement that often decides whether the settlement is positive at all on a low
grade lot.

Seed goes out by the truckload, weighed at the same scale the modules came over,
so a run has several seed loads rather than one figure. They are recorded as
they leave, which means the seed total for a run is not final when the run
closes: the last truck can be two days behind the last bale.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from ginstand.errors import StateError, ValidationError
from ginstand.store.book import Book
from ginstand.units.apportion import apportion, proportion
from ginstand.units.weight import check_pounds

SEED_GRACE_DAYS = 10
"""How long after a run closes a seed load can still be booked against it."""

LOW_SEED_TURNOUT = Decimal("0.4200")
HIGH_SEED_TURNOUT = Decimal("0.5600")
"""The band a run's seed turnout should land in. Outside it, a ticket is wrong."""


@dataclass(frozen=True, slots=True)
class SeedLoad:
    """One truckload of cottonseed off a run."""

    run: str
    weighed: date
    net_pounds: int
    ticket: str = ""
    buyer: str = ""
    load_id: int = 0


def record_load(
    book: Book,
    run_ref: str,
    on: date,
    net_pounds: int,
    ticket: str = "",
    buyer: str = "",
) -> SeedLoad:
    """Book a truckload of seed against a run."""
    run = book.runs.get(run_ref)
    check_pounds(net_pounds, "seed weight", minimum=1)
    if on < run.opened:
        raise StateError(
            f"{on.isoformat()} is before gin run {run.ref} opened on {run.opened.isoformat()}"
        )
    if run.closed is not None and on > run.closed + timedelta(days=SEED_GRACE_DAYS):
        raise StateError(
            f"gin run {run.ref} closed on {run.closed.isoformat()}, so a seed load "
            f"on {on.isoformat()} is past the {SEED_GRACE_DAYS} day grace"
        )
    cursor = book.connection.execute(
        "INSERT INTO seed_load (run, weighed, net_pounds, ticket, buyer) VALUES (?, ?, ?, ?, ?)",
        (run.ref, on.isoformat(), net_pounds, ticket.strip(), buyer.strip()),
    )
    return SeedLoad(
        run=run.ref,
        weighed=on,
        net_pounds=net_pounds,
        ticket=ticket.strip(),
        buyer=buyer.strip(),
        load_id=int(cursor.lastrowid or 0),
    )


def loads_for(book: Book, run_ref: str) -> tuple[SeedLoad, ...]:
    """Every seed load off a run, oldest first."""
    run = book.runs.get(run_ref)
    rows = book.connection.execute(
        "SELECT * FROM seed_load WHERE run = ? ORDER BY weighed, id", (run.ref,)
    ).fetchall()
    return tuple(
        SeedLoad(
            run=str(row["run"]),
            weighed=date.fromisoformat(str(row["weighed"])),
            net_pounds=int(row["net_pounds"]),
            ticket=str(row["ticket"]),
            buyer=str(row["buyer"]),
            load_id=int(row["id"]),
        )
        for row in rows
    )


def seed_pounds(book: Book, run_ref: str) -> int:
    """Every pound of seed booked against a run."""
    return sum(load.net_pounds for load in loads_for(book, run_ref))


def seed_turnout(book: Book, run_ref: str) -> Decimal:
    """Seed divided by seed cotton, to four places."""
    run = book.runs.get(run_ref)
    return proportion(seed_pounds(book, run.ref), book.runs.seed_cotton_in(run.ref))


def turnout_in_band(book: Book, run_ref: str) -> bool:
    """Whether the seed turnout is one the gin would not query."""
    figure = seed_turnout(book, run_ref)
    return LOW_SEED_TURNOUT <= figure <= HIGH_SEED_TURNOUT


def waste_pounds(book: Book, run_ref: str) -> int:
    """What went in less the lint and the seed that came out.

    Trash, moisture driven off, and whatever the mote system took. A negative
    figure is not possible, so it is refused rather than printed: it means a
    weight is wrong somewhere and the run's numbers cannot be trusted.
    """
    run = book.runs.get(run_ref)
    went_in = book.runs.seed_cotton_in(run.ref)
    came_out = book.bales.lint_pounds_for_run(run.ref) + seed_pounds(book, run.ref)
    if came_out > went_in:
        raise StateError(
            f"gin run {run.ref} produced {came_out:,} lb of lint and seed from "
            f"{went_in:,} lb of seed cotton, so a weight is wrong"
        )
    return went_in - came_out


def seed_by_producer(book: Book, run_ref: str, weights: dict[str, int]) -> dict[str, int]:
    """Split a run's seed between producers, pro rata by seed cotton."""
    if not weights:
        raise ValidationError("weights", "no producer put cotton into this run")
    total = seed_pounds(book, run_ref)
    producers = list(weights)
    shares = apportion(total, [weights[p] for p in producers])
    return dict(zip(producers, shares, strict=True))
