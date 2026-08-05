"""The laws, checked across a spread rather than at three points."""

from __future__ import annotations

from decimal import Decimal

import pytest

from ginstand.invariants import (
    AMOUNTS,
    CARRY_PLACES,
    COUNTS,
    POUNDS,
    READINGS,
    SHARES,
    WEIGHTS,
    apportionment_adds_back,
    bale_split_adds_back,
    carries_cancel,
    failures,
    holds,
    lease_split_adds_back,
    moisture_round_trips,
)


def test_every_law_holds_across_every_input() -> None:
    assert list(failures()) == []
    assert holds()


@pytest.mark.parametrize("weights", WEIGHTS)
@pytest.mark.parametrize("total", COUNTS)
def test_apportionment_never_loses_a_unit(total: int, weights: tuple[int, ...]) -> None:
    assert apportionment_adds_back(total, weights)


@pytest.mark.parametrize("weights", WEIGHTS)
@pytest.mark.parametrize("bales", COUNTS)
def test_every_bale_off_a_run_goes_to_somebody(bales: int, weights: tuple[int, ...]) -> None:
    assert bale_split_adds_back(bales, weights)


@pytest.mark.parametrize("weights", WEIGHTS)
@pytest.mark.parametrize("bales", COUNTS)
def test_the_carries_off_one_run_cancel_out(bales: int, weights: tuple[int, ...]) -> None:
    assert carries_cancel(bales, weights)


@pytest.mark.parametrize("share", SHARES)
@pytest.mark.parametrize("amount", AMOUNTS)
def test_a_lease_split_never_loses_a_cent(amount: int, share: str) -> None:
    assert lease_split_adds_back(amount, share)


@pytest.mark.parametrize("reading", READINGS)
@pytest.mark.parametrize("pounds", POUNDS)
def test_moisture_round_trips_within_a_pound(pounds: int, reading: str) -> None:
    assert moisture_round_trips(pounds, reading)


def test_the_awkward_weights_include_the_ones_that_divide_badly() -> None:
    assert (1, 1, 1) in WEIGHTS
    assert (33, 33, 34) in WEIGHTS
    assert any(0 in weights for weights in WEIGHTS)


def test_the_amounts_include_what_a_producer_owes() -> None:
    assert any(amount < 0 for amount in AMOUNTS)
    assert 0 in AMOUNTS


def test_the_carry_bound_is_one_millionth_per_producer() -> None:
    assert Decimal("0.000001") == CARRY_PLACES


def test_the_shares_include_the_ones_that_do_not_divide() -> None:
    assert "0.3333" in SHARES
    assert Decimal("0.3333") + Decimal("0.6667") == Decimal("1.0000")


def test_a_broken_law_is_reported_with_its_input() -> None:
    assert apportionment_adds_back(10, (1, 1)) is not False
    assert list(failures()) == []


def test_a_law_that_does_not_hold_is_reported_with_its_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every law has to have been seen to fire, not only to pass."""
    for name, wanted in (
        ("apportionment_adds_back", "apportionment lost a unit"),
        ("bale_split_adds_back", "a bale went missing"),
        ("carries_cancel", "the carries do not cancel"),
        ("lease_split_adds_back", "a lease split lost a cent"),
        ("moisture_round_trips", "moisture did not round trip"),
    ):

        def never(*_args: object, **_kwargs: object) -> bool:
            return False

        monkeypatch.setattr(f"ginstand.invariants.{name}", never)
        broken = list(failures())
        assert any(wanted in message for message in broken), name
        assert not holds()
        monkeypatch.undo()
