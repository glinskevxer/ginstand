"""The workflow runs commands that exist, and runs every check there is."""

from __future__ import annotations

from ginstand.tools.base import repo_root
from ginstand.tools.check_workflow import (
    WORKFLOW,
    checks_in_the_package,
    checks_in_the_workflow,
    findings,
    missing_command,
    workflow_lines,
)


def test_the_workflow_names_only_commands_and_checks_that_exist() -> None:
    assert list(findings()) == []


def test_the_workflow_is_where_the_check_looks() -> None:
    assert (repo_root() / WORKFLOW).is_file()
    assert any("ginstand --book" in line for line in workflow_lines())


def test_the_continuations_are_joined_before_reading() -> None:
    assert not any(line.endswith("\\") for line in workflow_lines())


def test_a_real_command_is_not_missing() -> None:
    assert missing_command(["run", "press"]) is None
    assert missing_command(["report", "season"]) is None


def test_arguments_after_a_command_are_not_walked() -> None:
    assert missing_command(["producer", "add", "P-12", "Aldys"]) is None


def test_a_command_that_does_not_exist_is_named() -> None:
    assert missing_command(["run", "unpress"]) == "run unpress"
    assert missing_command(["nowhere"]) == "nowhere"


def test_every_check_in_the_package_is_run_by_the_workflow() -> None:
    package = set(checks_in_the_package())
    workflow = set(checks_in_the_workflow())
    assert package <= workflow


def test_the_workflow_runs_the_checks_worth_naming() -> None:
    running = checks_in_the_workflow()
    for name in ("check_clock", "check_layers", "check_sql", "smoke"):
        assert name in running


def test_the_package_offers_a_useful_number_of_checks() -> None:
    assert len(checks_in_the_package()) >= 12
