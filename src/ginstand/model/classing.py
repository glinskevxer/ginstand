"""The classing card that comes back from the office for one bale.

Everything on this record was measured by somebody else. The gin does not get to
argue with it, only to ask for a recheck, so the record is exactly what arrived
and nothing here is derived or corrected.

The one judgement the record does make is whether the card itself says below
grade. That reads off the colour and the leaf, which are the two things the card
grades. It deliberately does not consider extraneous matter, because the rule
that puts a plastic contaminated bale off the schedule is a rule of ours rather
than a grade on the card, and mixing the two makes it impossible to see which
one put a bale where it ended up.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from ginstand.errors import ValidationError
from ginstand.grades.color import ColorGrade
from ginstand.grades.matter import Extraneous, carries_plastic, leaf_below_grade, leaf_grade
from ginstand.ids import parse_pbi
from ginstand.units.staple import check_staple

MIN_MICRONAIRE = Decimal("2.0")
MAX_MICRONAIRE = Decimal("7.0")
MIN_STRENGTH = Decimal("15.0")
MAX_STRENGTH = Decimal("45.0")
MIN_UNIFORMITY = Decimal("65.0")
MAX_UNIFORMITY = Decimal("95.0")
MAX_TRASH = Decimal("10.0")

_ONE_PLACE = Decimal("0.1")


def _reading(value: Decimal | str | int, name: str, low: Decimal, high: Decimal) -> Decimal:
    reading = Decimal(value).quantize(_ONE_PLACE, rounding=ROUND_HALF_UP)
    if reading < low or reading > high:
        raise ValidationError(name, f"must be between {low} and {high}, got {reading}")
    return reading


@dataclass(frozen=True, slots=True)
class Classing:
    """One bale's classing card."""

    tag: str
    classed: date
    color: ColorGrade
    leaf: int
    staple: int
    micronaire: Decimal
    strength: Decimal
    uniformity: Decimal
    trash_pct: Decimal = Decimal("0.0")
    extraneous: tuple[Extraneous, ...] = field(default=())
    office: str = ""
    remarks: str = ""

    def __post_init__(self) -> None:
        parse_pbi(self.tag)
        object.__setattr__(self, "tag", self.tag.strip().replace(" ", "").replace("-", ""))
        leaf_grade(self.leaf)
        check_staple(self.staple)
        object.__setattr__(
            self,
            "micronaire",
            _reading(self.micronaire, "micronaire", MIN_MICRONAIRE, MAX_MICRONAIRE),
        )
        object.__setattr__(
            self, "strength", _reading(self.strength, "strength", MIN_STRENGTH, MAX_STRENGTH)
        )
        object.__setattr__(
            self,
            "uniformity",
            _reading(self.uniformity, "uniformity", MIN_UNIFORMITY, MAX_UNIFORMITY),
        )
        object.__setattr__(
            self, "trash_pct", _reading(self.trash_pct, "trash", Decimal("0.0"), MAX_TRASH)
        )
        object.__setattr__(self, "extraneous", tuple(sorted(set(self.extraneous))))
        object.__setattr__(self, "office", self.office.strip().upper())
        object.__setattr__(self, "remarks", self.remarks.strip())

    @property
    def below_grade_on_card(self) -> bool:
        """Whether the card grades this bale below grade on colour or on leaf."""
        return self.color.below_grade or leaf_below_grade(self.leaf)

    @property
    def carries_plastic(self) -> bool:
        """Whether the classer noted plastic, at either level."""
        return carries_plastic(self.extraneous)

    @property
    def codes(self) -> str:
        """The extraneous matter notes as one printable run of codes."""
        return " ".join(note.code for note in self.extraneous)

    @property
    def summary(self) -> str:
        """The one line the office reads off a bale list."""
        parts = [f"{self.color.code}-{self.leaf}", f"{self.staple}", f"mic {self.micronaire}"]
        if self.extraneous:
            parts.append(self.codes)
        return " ".join(parts)
