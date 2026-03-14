"""An account entry keeps its sign from the producer's side."""

from __future__ import annotations

from datetime import date

import pytest

from ginstand.errors import ValidationError
from ginstand.model.account import Entry, EntryKind
from ginstand.units.money import money

MADE = date(2025, 11, 3)


def an_entry(**changes: object) -> Entry:
    fields: dict[str, object] = {
        "producer": "p-12",
        "crop_year": 2025,
        "made": MADE,
        "kind": EntryKind.SETTLEMENT,
        "amount": money("1816.80"),
        "run": "gr-1",
    }
    fields.update(changes)
    return Entry(**fields)  # type: ignore[arg-type]


def test_an_entry_normalises_its_references() -> None:
    entry = an_entry()
    assert entry.producer == "P-12"
    assert entry.run == "GR-1"


def test_a_settlement_the_producer_is_owed_is_positive() -> None:
    assert an_entry().owed_to_producer


def test_a_settlement_the_producer_owes_is_negative() -> None:
    assert not an_entry(amount=money("-40.00")).owed_to_producer


def test_an_entry_of_nothing_is_not_an_entry() -> None:
    with pytest.raises(ValidationError, match="a settlement of nothing"):
        an_entry(amount=money("0"))


def test_a_settlement_names_the_run_it_settles() -> None:
    with pytest.raises(ValidationError, match="names the run it settles"):
        an_entry(run="")


def test_a_payment_moves_money_to_the_producer_so_it_is_negative() -> None:
    payment = an_entry(kind=EntryKind.PAYMENT, amount=money("-1000.00"), run="")
    assert payment.amount < 0
    with pytest.raises(ValidationError, match="so it is negative"):
        an_entry(kind=EntryKind.PAYMENT, amount=money("1000.00"), run="")


def test_an_adjustment_can_go_either_way() -> None:
    assert an_entry(kind=EntryKind.ADJUSTMENT, amount=money("40.00"), run="").amount > 0
    assert an_entry(kind=EntryKind.ADJUSTMENT, amount=money("-40.00"), run="").amount < 0


def test_an_adjustment_may_name_a_run_or_not() -> None:
    assert an_entry(kind=EntryKind.ADJUSTMENT, amount=money("40.00")).run == "GR-1"
    assert an_entry(kind=EntryKind.ADJUSTMENT, amount=money("40.00"), run="").run == ""


def test_a_crop_year_this_package_cannot_file_is_refused() -> None:
    with pytest.raises(ValidationError, match="between 2000 and 2099"):
        an_entry(crop_year=1999)


def test_the_line_names_the_run_or_the_reference() -> None:
    assert "GR-1" in an_entry().line
    payment = an_entry(
        kind=EntryKind.PAYMENT, amount=money("-1000.00"), run="", reference="CHQ-4471"
    )
    assert "CHQ-4471" in payment.line
    bare = an_entry(kind=EntryKind.ADJUSTMENT, amount=money("40.00"), run="")
    assert "-" in bare.line


def test_an_entry_is_frozen() -> None:
    entry = an_entry()
    with pytest.raises(AttributeError):
        entry.amount = money("1.00")  # type: ignore[misc]
