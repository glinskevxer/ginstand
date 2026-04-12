"""Which bales to pull off a run and check, and what the answer means.

Check weighing every bale is not worth the time and checking none of them is how
a press setting drifts for a fortnight. So a sample is pulled, and the size of
the sample comes off the size of the run rather than being a fixed number: a
sample of eight is most of a twelve bale run and nothing at all of a four
hundred bale one.

Then the verdict comes off the sample size. The number of bad bales that fails a
sample is not a fixed fraction either, because a bigger sample tolerates a bad
one and still says the run is fine. So the run's size decides the sample size,
and the sample size decides what counts as a failure. Neither number means
anything without the other, which is why they are one table and not two.

The bales are pulled evenly across the run rather than at random. A press
setting drifts in one direction over a run, and evenly spaced bales find that
where a random handful from the middle does not.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ginstand.errors import StateError, ValidationError
from ginstand.store.book import Book


class Verdict(StrEnum):
    """What a check weigh sample came to."""

    ACCEPT = "accept"
    """The run passes. Nothing to do."""

    LOOK = "look"
    """Between the two numbers. Pull a second sample before deciding."""

    REJECT = "reject"
    """The run fails. Every bale gets weighed and the press gets looked at."""


@dataclass(frozen=True, slots=True)
class Plan:
    """One rung of the sampling table."""

    smallest_lot: int
    sample: int
    accept: int
    reject: int

    def __post_init__(self) -> None:
        if self.accept >= self.reject:
            raise ValidationError(
                "plan",
                f"accepting at {self.accept} and rejecting at {self.reject} leaves "
                f"nothing in between",
            )
        if self.reject > self.sample:
            raise ValidationError(
                "plan", f"a sample of {self.sample} cannot have {self.reject} bad bales"
            )

    def verdict(self, defects: int) -> Verdict:
        """What a count of bad bales in this sample means."""
        if defects < 0:
            raise ValidationError("defects", "must not be negative")
        if defects > self.sample:
            raise ValidationError(
                "defects", f"{defects} bad bales out of a sample of {self.sample}"
            )
        if defects <= self.accept:
            return Verdict.ACCEPT
        if defects >= self.reject:
            return Verdict.REJECT
        return Verdict.LOOK


TABLE: tuple[Plan, ...] = (
    Plan(smallest_lot=1, sample=2, accept=0, reject=1),
    Plan(smallest_lot=9, sample=3, accept=0, reject=2),
    Plan(smallest_lot=26, sample=5, accept=1, reject=2),
    Plan(smallest_lot=51, sample=8, accept=1, reject=3),
    Plan(smallest_lot=91, sample=13, accept=2, reject=4),
    Plan(smallest_lot=151, sample=20, accept=3, reject=5),
    Plan(smallest_lot=281, sample=32, accept=5, reject=7),
)
"""The sampling table, by the smallest lot each rung covers."""


def plan_for(lot: int) -> Plan:
    """The rung of the table a lot of this size falls on."""
    if lot < 1:
        raise ValidationError("lot", "must have at least one bale in it")
    found = TABLE[0]
    for rung in TABLE:
        if lot >= rung.smallest_lot:
            found = rung
    return found


def positions(lot: int, sample: int) -> tuple[int, ...]:
    """Which places in the run to pull from, evenly spaced and one based."""
    if sample <= 0:
        raise ValidationError("sample", "must be at least one bale")
    if sample >= lot:
        return tuple(range(1, lot + 1))
    step = lot / sample
    return tuple(sorted({int(step * (index + 0.5)) + 1 for index in range(sample)}))


def sample_for(book: Book, run_ref: str) -> tuple[str, ...]:
    """The bale tags to pull off a run and check weigh."""
    run = book.runs.get(run_ref)
    bales = book.bales.for_run(run.ref)
    if not bales:
        raise StateError(f"gin run {run.ref} has pressed no bales")
    plan = plan_for(len(bales))
    return tuple(bales[place - 1].tag for place in positions(len(bales), plan.sample))


def judge(book: Book, run_ref: str, defects: int) -> Verdict:
    """What a run's check weigh comes to, given how many bales were bad."""
    run = book.runs.get(run_ref)
    lot = book.bales.count_for_run(run.ref)
    if lot == 0:
        raise StateError(f"gin run {run.ref} has pressed no bales")
    return plan_for(lot).verdict(defects)


def explain(lot: int) -> str:
    """The plan for a lot, as one printable line."""
    plan = plan_for(lot)
    return f"{lot} bales: pull {plan.sample}, accept on {plan.accept}, reject on {plan.reject}"
