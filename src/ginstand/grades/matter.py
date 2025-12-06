"""Leaf grade and extraneous matter: the two things in a bale that are not lint.

Leaf is the fine plant material the gin's cleaners did not take out. It is
graded one to seven, and eight means the sample is below grade on leaf alone.
Leaf is priced, and the price depends on the colour grade, so leaf never stands
on its own in a schedule.

Extraneous matter is anything that should not be there at all: bark, grass, seed
coat fragments, oil, and plastic. It is not graded, it is noted, with a level of
light or heavy. Plastic is the one everybody watches, because a round module's
wrap is plastic and a spinner who finds it in a bale stops buying from that gin.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum

from ginstand.errors import ValidationError

BEST_LEAF = 1
WORST_LEAF = 7
BELOW_GRADE_LEAF = 8


def leaf_grade(value: int, field: str = "leaf grade") -> int:
    """Return ``value`` if it is a leaf grade the card can carry."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(field, "must be a whole number from 1 to 8")
    if value < BEST_LEAF or value > BELOW_GRADE_LEAF:
        raise ValidationError(
            field, f"must be between {BEST_LEAF} and {BELOW_GRADE_LEAF}, got {value}"
        )
    return value


def leaf_below_grade(value: int) -> bool:
    """Whether a leaf grade puts the bale off the schedule on its own."""
    return leaf_grade(value) == BELOW_GRADE_LEAF


class ExtraneousKind(StrEnum):
    """What the classer found that is not cotton."""

    BARK = "bark"
    GRASS = "grass"
    SEED_COAT = "seed coat"
    PREPARATION = "preparation"
    OIL = "oil"
    PLASTIC = "plastic"
    OTHER = "other"


class ExtraneousLevel(IntEnum):
    """How much of it there was."""

    LIGHT = 1
    HEAVY = 2


KIND_CODES: dict[ExtraneousKind, str] = {
    ExtraneousKind.BARK: "BK",
    ExtraneousKind.GRASS: "GR",
    ExtraneousKind.SEED_COAT: "SC",
    ExtraneousKind.PREPARATION: "PR",
    ExtraneousKind.OIL: "OL",
    ExtraneousKind.PLASTIC: "PL",
    ExtraneousKind.OTHER: "OT",
}

_CODE_KINDS = {code: kind for kind, code in KIND_CODES.items()}


@dataclass(frozen=True, slots=True, order=True)
class Extraneous:
    """One extraneous matter note off a classing card."""

    kind: ExtraneousKind
    level: ExtraneousLevel = ExtraneousLevel.LIGHT

    @property
    def code(self) -> str:
        """The two letters and the level, as the card prints it."""
        return f"{KIND_CODES[self.kind]}{int(self.level)}"

    @property
    def heavy(self) -> bool:
        """Whether the classer called it heavy."""
        return self.level is ExtraneousLevel.HEAVY

    def __str__(self) -> str:
        return self.code


def parse_extraneous(text: str, field: str = "extraneous matter") -> Extraneous:
    """Read one extraneous matter note off a card."""
    cleaned = text.strip().upper()
    if len(cleaned) != 3:
        raise ValidationError(field, f"must be two letters and a level, got {text!r}")
    code, level = cleaned[:2], cleaned[2]
    if code not in _CODE_KINDS:
        raise ValidationError(field, f"{code} is not an extraneous matter code")
    if level not in ("1", "2"):
        raise ValidationError(field, f"level must be 1 or 2, got {level!r}")
    return Extraneous(kind=_CODE_KINDS[code], level=ExtraneousLevel(int(level)))


def carries_plastic(notes: tuple[Extraneous, ...]) -> bool:
    """Whether any note on the card is plastic, at either level."""
    return any(note.kind is ExtraneousKind.PLASTIC for note in notes)
