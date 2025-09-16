"""Collecting everything a settlement needs about one producer's share of a run.

Gathering is separate from working out the money because the two go wrong in
different ways and it is worth being able to see which happened. A settlement
that comes out short is either short of facts or short of arithmetic, and a
statement that cannot say which one is not answerable.

The awkward part is leases. Bales are allocated to a producer, but a producer
may have fed the same run off two fields under two different leases, and it is
the lease that decides who the settlement gets split with. So the share carries
the seed cotton behind it broken down by lease, and the money is spread across
those leases in the same proportion.
"""

from __future__ import annotations

from dataclasses import dataclass

from ginstand.errors import StateError
from ginstand.ids import reference
from ginstand.store.book import Book
from ginstand.yard.receiving import producer_of


@dataclass(frozen=True, slots=True)
class RunShare:
    """One producer's part of one gin run, as facts rather than as money."""

    run: str
    crop_year: int
    producer: str
    module_tags: tuple[str, ...]
    seed_cotton_pounds: int
    bale_tags: tuple[str, ...]
    lint_pounds: int
    classed: tuple[str, ...]
    unclassed: tuple[str, ...]
    lease_pounds: dict[str, int]

    @property
    def modules(self) -> int:
        """How many modules this producer put into the run."""
        return len(self.module_tags)

    @property
    def bales(self) -> int:
        """How many bales came back to them."""
        return len(self.bale_tags)

    @property
    def complete(self) -> bool:
        """Whether every bale in the share has a classing card."""
        return not self.unclassed

    @property
    def leases(self) -> tuple[str, ...]:
        """The leases behind this share, in reference order."""
        return tuple(sorted(self.lease_pounds))

    @property
    def line(self) -> str:
        """The line a run's settlement list prints."""
        waiting = f", {len(self.unclassed)} unclassed" if self.unclassed else ""
        return (
            f"{self.producer}  {self.modules} modules  "
            f"{self.seed_cotton_pounds:,} lb  {self.bales} bales{waiting}"
        )


def gather(book: Book, run_ref: str, producer: str) -> RunShare:
    """Collect one producer's share of a closed, allocated run."""
    run = book.runs.get(run_ref)
    who = book.producers.get(producer).ref
    if run.is_open:
        raise StateError(f"gin run {run.ref} is still open, so it cannot be settled")
    if not book.allocations.run_is_allocated(run.ref):
        raise StateError(f"gin run {run.ref} has not been allocated yet")

    module_tags = []
    seed_cotton = 0
    lease_pounds: dict[str, int] = {}
    for tag in book.runs.modules_in(run.ref):
        if producer_of(book, tag) != who:
            continue
        module = book.modules.get(tag)
        module_tags.append(module.tag)
        seed_cotton += module.net_pounds
        lease = book.fields.get(module.field).lease
        lease_pounds[lease] = lease_pounds.get(lease, 0) + module.net_pounds

    bale_tags = []
    lint = 0
    classed = []
    unclassed = []
    for tag, owner in book.allocations.bales_for_run(run.ref).items():
        if owner != who:
            continue
        bale_tags.append(tag)
        lint += book.bales.get(tag).net_pounds
        if book.cards.exists(tag):
            classed.append(tag)
        else:
            unclassed.append(tag)

    if not module_tags and not bale_tags:
        raise StateError(f"producer {who} has nothing on gin run {run.ref}")

    return RunShare(
        run=run.ref,
        crop_year=run.crop_year,
        producer=who,
        module_tags=tuple(module_tags),
        seed_cotton_pounds=seed_cotton,
        bale_tags=tuple(bale_tags),
        lint_pounds=lint,
        classed=tuple(classed),
        unclassed=tuple(unclassed),
        lease_pounds=lease_pounds,
    )


def producers_in(book: Book, run_ref: str) -> tuple[str, ...]:
    """Every producer with cotton in a run, in the order they fed."""
    seen: list[str] = []
    for tag in book.runs.modules_in(reference(run_ref, "gin run")):
        owner = producer_of(book, tag)
        if owner not in seen:
            seen.append(owner)
    return tuple(seen)


def gather_all(book: Book, run_ref: str) -> tuple[RunShare, ...]:
    """Every producer's share of a run, in feed order."""
    return tuple(gather(book, run_ref, producer) for producer in producers_in(book, run_ref))
