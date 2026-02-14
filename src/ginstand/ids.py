"""The references this package puts on records, and the bale tag.

Two kinds of identifier live here. Most records carry a short office reference
that a person typed: a producer number, a field number, a gin run number. Those
are normalised and checked but their shape is the office's business.

The bale tag is different. It is the permanent bale identification and it goes
on the bale, on the sample, on the classing card and on the warehouse receipt.
Twelve digits: two for the crop year, five for the gin code the classing office
assigned us, five for the bale's sequence within that crop year. It is the one
identifier in the system that outside parties also read, so it is built and
parsed here rather than formatted at each place it is printed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ginstand.errors import ValidationError

REFERENCE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{0,22}[A-Z0-9]$")
"""Two to twenty four characters, upper case, digits and inner dashes."""

GIN_CODE_DIGITS = 5
BALE_SEQUENCE_DIGITS = 5
PBI_DIGITS = 2 + GIN_CODE_DIGITS + BALE_SEQUENCE_DIGITS

MAX_BALE_SEQUENCE = 10**BALE_SEQUENCE_DIGITS - 1


def reference(value: str, kind: str = "reference") -> str:
    """Normalise an office reference and check its shape.

    Upper cased and stripped, because the same producer gets typed three ways in
    a season and they are all meant to be the one producer.
    """
    cleaned = value.strip().upper()
    if not cleaned:
        raise ValidationError(kind, "is empty")
    if not REFERENCE_PATTERN.match(cleaned):
        raise ValidationError(
            kind,
            f"must be 2 to 24 characters of letters, digits and inner dashes, got {value!r}",
        )
    return cleaned


def gin_code(value: str) -> str:
    """The five digit code the classing office issued to this gin."""
    cleaned = value.strip()
    if not cleaned.isdigit() or len(cleaned) != GIN_CODE_DIGITS:
        raise ValidationError("gin code", f"must be {GIN_CODE_DIGITS} digits, got {value!r}")
    return cleaned


def _crop_year_digits(crop_year: int) -> str:
    if crop_year < 2000 or crop_year > 2099:
        raise ValidationError("crop year", f"must be between 2000 and 2099, got {crop_year}")
    return f"{crop_year % 100:02d}"


@dataclass(frozen=True, slots=True)
class Pbi:
    """A permanent bale identification, split into the parts it is built from."""

    crop_year: int
    gin_code: str
    sequence: int

    @property
    def tag(self) -> str:
        """The twelve digits as they are printed on the bale."""
        return f"{_crop_year_digits(self.crop_year)}{self.gin_code}{self.sequence:05d}"

    def __str__(self) -> str:
        return self.tag


def make_pbi(crop_year: int, code: str, sequence: int) -> Pbi:
    """Build a bale tag from its parts, checking each one."""
    _crop_year_digits(crop_year)
    checked_code = gin_code(code)
    if isinstance(sequence, bool) or not isinstance(sequence, int):
        raise ValidationError("bale sequence", "must be a whole number")
    if sequence < 1 or sequence > MAX_BALE_SEQUENCE:
        raise ValidationError(
            "bale sequence", f"must be between 1 and {MAX_BALE_SEQUENCE}, got {sequence}"
        )
    return Pbi(crop_year=crop_year, gin_code=checked_code, sequence=sequence)


def bale_tag(text: str) -> str:
    """Normalise a bale tag to the twelve digits that go in the book.

    Every record and every store that keys on a tag needs this, and each of them
    had its own copy of it for a while. Two of the copies had drifted: one of
    them checked the tag first and one of them did not, so a badly typed tag was
    a clear message from one store and a missing row from another.
    """
    parse_pbi(text)
    return text.strip().replace(" ", "").replace("-", "")


def parse_pbi(text: str) -> Pbi:
    """Read a bale tag off a card, a receipt or a scanner.

    Spaces and dashes are tolerated because the tag is printed in groups on some
    documents and read as one run of digits by the scanner.
    """
    cleaned = text.strip().replace(" ", "").replace("-", "")
    if not cleaned.isdigit() or len(cleaned) != PBI_DIGITS:
        raise ValidationError("bale tag", f"must be {PBI_DIGITS} digits, got {text!r}")
    year_part = int(cleaned[:2])
    code = cleaned[2 : 2 + GIN_CODE_DIGITS]
    sequence = int(cleaned[2 + GIN_CODE_DIGITS :])
    if sequence < 1:
        raise ValidationError("bale tag", "carries bale sequence 0, which is never issued")
    return Pbi(crop_year=2000 + year_part, gin_code=code, sequence=sequence)
