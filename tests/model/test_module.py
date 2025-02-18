"""A module is what the scale ticket said, and it does not change afterwards."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from ginstand.errors import ValidationError
from ginstand.model.module import (
    MAX_MODULE_POUNDS,
    MIN_MODULE_POUNDS,
    Module,
    ModuleKind,
    WrapKind,
)


def a_module(**changes: object) -> Module:
    fields: dict[str, object] = {
        "tag": "m-4471",
        "field": "fl-9",
        "kind": ModuleKind.RECTANGULAR,
        "harvested": date(2025, 9, 30),
        "received": date(2025, 10, 2),
        "gross_pounds": 48_200,
        "tare_pounds": 26_140,
        "moisture_pct": Decimal("11.4"),
        "wrap": WrapKind.TARP,
    }
    fields.update(changes)
    return Module(**fields)  # type: ignore[arg-type]


def test_a_module_normalises_its_references() -> None:
    module = a_module()
    assert module.tag == "M-4471"
    assert module.field == "FL-9"


def test_net_weight_is_gross_less_tare() -> None:
    assert a_module().net_pounds == 22_060


def test_dry_weight_comes_off_the_moisture_reading() -> None:
    assert a_module(moisture_pct=Decimal("10.0")).dry_pounds == 19_854


def test_days_in_field_is_harvest_to_scale() -> None:
    assert a_module().days_in_field == 2
    assert a_module(harvested=date(2025, 10, 2)).days_in_field == 0


def test_a_module_lighter_than_a_partial_load_is_refused() -> None:
    with pytest.raises(ValidationError, match=f"at least {MIN_MODULE_POUNDS} lb for a module"):
        a_module(gross_pounds=26_400, tare_pounds=26_140)


def test_two_modules_weighed_as_one_are_refused() -> None:
    with pytest.raises(ValidationError, match=f"no more than {MAX_MODULE_POUNDS} lb"):
        a_module(gross_pounds=90_000, tare_pounds=1_000)


def test_a_reversed_ticket_is_caught_before_the_module_exists() -> None:
    with pytest.raises(ValidationError, match="check the ticket"):
        a_module(gross_pounds=26_140, tare_pounds=48_200)


def test_a_module_received_before_it_was_harvested_is_refused() -> None:
    with pytest.raises(ValidationError, match="before the module was harvested"):
        a_module(received=date(2025, 9, 29))


def test_a_round_module_is_always_wrapped_in_film() -> None:
    with pytest.raises(ValidationError, match="wrapped in film"):
        a_module(kind=ModuleKind.ROUND, wrap=WrapKind.TARP)
    assert a_module(kind=ModuleKind.ROUND, wrap=WrapKind.FILM).carries_plastic


def test_only_film_brings_plastic_into_the_gin() -> None:
    assert not a_module(wrap=WrapKind.TARP).carries_plastic
    assert not a_module(kind=ModuleKind.TRAILER, wrap=WrapKind.NONE).carries_plastic


def test_the_moisture_reading_is_quantised_on_the_way_in() -> None:
    assert a_module(moisture_pct=Decimal("11.44")).moisture_pct == Decimal("11.4")


def test_a_moisture_reading_off_the_meter_range_is_refused() -> None:
    with pytest.raises(ValidationError, match="no more than 25.0%"):
        a_module(moisture_pct=Decimal("30"))


def test_a_module_is_frozen() -> None:
    module = a_module()
    with pytest.raises(AttributeError):
        module.gross_pounds = 1  # type: ignore[misc]


def test_the_kinds_read_as_the_words_the_yard_uses() -> None:
    assert str(ModuleKind.ROUND) == "round"
    assert str(WrapKind.FILM) == "film"
    assert ModuleKind("trailer") is ModuleKind.TRAILER
