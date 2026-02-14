"""Bales, as they come off the press.

The bale is the unit everything downstream deals in. The classing office reads a
sample off it, the loan schedule prices it, the warehouse issues a receipt
against it and the producer is paid for it. It carries a permanent bale
identification tag that all four of those parties use.

Weights on a bale are gross at the press, the tare of the bagging and ties, and
the net that follows. The net is what gets valued, so the tare is a record in
its own right rather than a constant applied later: a gin that changes bagging
supplier mid season changes its tare, and last season's bales keep the old one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from ginstand.errors import ValidationError
from ginstand.ids import Pbi, bale_tag, parse_pbi, reference
from ginstand.units.moisture import dry_weight, moisture, safe_to_store
from ginstand.units.weight import check_pounds, net_of

MIN_BALE_POUNDS = 300
"""A press cycle that produced less than this did not make a saleable bale."""

MAX_BALE_POUNDS = 750
"""Past this the press did not release, or two cycles were weighed together."""

MIN_TARE_POUNDS = 4
MAX_TARE_POUNDS = 40
"""Bagging and eight ties. Outside this range the tare was typed wrong."""


@dataclass(frozen=True, slots=True)
class Bale:
    """One pressed bale of lint."""

    tag: str
    run: str
    pressed: date
    gross_pounds: int
    tare_pounds: int
    moisture_pct: Decimal
    stand: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "tag", bale_tag(self.tag))
        object.__setattr__(self, "run", reference(self.run, "gin run"))
        check_pounds(self.gross_pounds, "gross weight")
        if self.tare_pounds < MIN_TARE_POUNDS or self.tare_pounds > MAX_TARE_POUNDS:
            raise ValidationError(
                "tare weight",
                f"bagging and ties weigh {MIN_TARE_POUNDS} to {MAX_TARE_POUNDS} lb, "
                f"got {self.tare_pounds}",
            )
        net = net_of(self.gross_pounds, self.tare_pounds)
        if net < MIN_BALE_POUNDS:
            raise ValidationError(
                "net weight", f"must be at least {MIN_BALE_POUNDS} lb for a bale, got {net}"
            )
        if net > MAX_BALE_POUNDS:
            raise ValidationError(
                "net weight", f"must be no more than {MAX_BALE_POUNDS} lb, got {net}"
            )
        object.__setattr__(self, "moisture_pct", moisture(self.moisture_pct))
        object.__setattr__(self, "stand", self.stand.strip())

    @property
    def net_pounds(self) -> int:
        """Lint weight, which is what the loan schedule prices."""
        return self.gross_pounds - self.tare_pounds

    @property
    def dry_pounds(self) -> int:
        """The dry lint in the bale."""
        return dry_weight(self.net_pounds, self.moisture_pct)

    @property
    def pbi(self) -> Pbi:
        """The tag split into crop year, gin code and sequence."""
        return parse_pbi(self.tag)

    @property
    def crop_year(self) -> int:
        """The crop year the tag files this bale under."""
        return self.pbi.crop_year

    @property
    def sequence(self) -> int:
        """This bale's number within the crop year."""
        return self.pbi.sequence

    @property
    def storable(self) -> bool:
        """Whether the bale can go to the warehouse at the moisture it was pressed at."""
        return safe_to_store(self.moisture_pct)
