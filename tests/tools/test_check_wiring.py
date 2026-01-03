"""The wiring check, and the package passing it."""

from __future__ import annotations

from ginstand.tools.check_wiring import ENTRY, EXEMPT, findings, reachable


def test_every_module_is_reachable_from_the_command_line() -> None:
    assert list(findings()) == []


def test_the_entry_point_reaches_itself() -> None:
    assert ENTRY in reachable()


def test_the_rules_are_reached_through_the_commands() -> None:
    found = reachable()
    for dotted in (
        "ginstand.yard.order",
        "ginstand.ginning.allocate",
        "ginstand.loan.value",
        "ginstand.settle.statement",
        "ginstand.warehouse.storage",
        "ginstand.report.season",
    ):
        assert dotted in found


def test_a_parent_package_is_reached_with_its_children() -> None:
    found = reachable()
    assert "ginstand.units" in found
    assert "ginstand.grades" in found


def test_a_from_package_import_module_is_followed() -> None:
    assert "ginstand.cli.growers" in reachable()


def test_the_checks_are_exempt_because_ci_runs_them() -> None:
    assert "ginstand.tools" in EXEMPT
    assert "ginstand.tools.check_wiring" not in reachable()


def test_reaching_from_somewhere_else_reaches_less() -> None:
    from_units = reachable("ginstand.units.weight")
    assert "ginstand.units.weight" in from_units
    assert "ginstand.settle.statement" not in from_units


def test_an_entry_point_that_is_not_a_module_reaches_nothing() -> None:
    assert reachable("ginstand.nowhere") == frozenset()
