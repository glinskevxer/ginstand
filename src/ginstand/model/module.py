"""Modules of seed cotton, as they are weighed in at the gin.

A module is the unit the yard works in. It arrives on a truck, crosses the
scale, gets a moisture reading and a place in a row, and later gets fed into a
gin run. This record is what the scale ticket says and it does not change after
that: where the module is and whether it has been ginned are the yard's business
and live in their own records.

Round modules come off the picker wrapped in plastic film. That film is the
single largest contamination risk in a modern gin, and the wrap type is kept
here because the yard rules and the classing remarks both turn on it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from ginstand.errors import ValidationError
from ginstand.ids import reference
from ginstand.units.moisture import dry_weight, moisture
from ginstand.units.weight import check_pounds, net_of

MIN_MODULE_POUNDS = 500
"""Lighter than this is a partial load or a scale that did not settle."""

MAX_MODULE_POUNDS = 60_000
"""Heavier than this is two modules weighed as one."""


class ModuleKind(StrEnum):
    """How the seed cotton was packaged in the field."""

    ROUND = "round"
    """Off a round module picker, wrapped in plastic film."""

    RECTANGULAR = "rectangular"
    """Off a module builder, tarped rather than wrapped."""

    TRAILER = "trailer"
    """Loose in a trailer. Older kit, and it still turns up."""


class WrapKind(StrEnum):
    """What is around the module, which is what can end up in the lint."""

    NONE = "none"
    FILM = "film"
    TARP = "tarp"


@dataclass(frozen=True, slots=True)
class Module:
    """One module of seed cotton, as weighed in."""

    tag: str
    field: str
    kind: ModuleKind
    harvested: date
    received: date
    gross_pounds: int
    tare_pounds: int
    moisture_pct: Decimal
    wrap: WrapKind = WrapKind.NONE
    variety: str = ""
    note: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "tag", reference(self.tag, "module tag"))
        object.__setattr__(self, "field", reference(self.field, "field"))
        check_pounds(self.gross_pounds, "gross weight")
        check_pounds(self.tare_pounds, "tare weight")
        net = net_of(self.gross_pounds, self.tare_pounds)
        if net < MIN_MODULE_POUNDS:
            raise ValidationError(
                "net weight", f"must be at least {MIN_MODULE_POUNDS} lb for a module, got {net}"
            )
        if net > MAX_MODULE_POUNDS:
            raise ValidationError(
                "net weight", f"must be no more than {MAX_MODULE_POUNDS} lb, got {net}"
            )
        if self.received < self.harvested:
            raise ValidationError(
                "received",
                f"{self.received.isoformat()} is before the module was harvested "
                f"on {self.harvested.isoformat()}",
            )
        if self.kind is ModuleKind.ROUND and self.wrap is not WrapKind.FILM:
            raise ValidationError("wrap", "a round module is wrapped in film")
        object.__setattr__(self, "moisture_pct", moisture(self.moisture_pct))
        object.__setattr__(self, "variety", self.variety.strip())
        object.__setattr__(self, "note", self.note.strip())

    @property
    def net_pounds(self) -> int:
        """Seed cotton on the ticket, gross less tare."""
        return self.gross_pounds - self.tare_pounds

    @property
    def dry_pounds(self) -> int:
        """The dry matter in the module, which is what survives the dryers."""
        return dry_weight(self.net_pounds, self.moisture_pct)

    @property
    def days_in_field(self) -> int:
        """How long the module sat between harvest and the scale."""
        return (self.received - self.harvested).days

    @property
    def carries_plastic(self) -> bool:
        """Whether this module brings plastic film into the gin."""
        return self.wrap is WrapKind.FILM
