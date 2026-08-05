"""The help check, and the command line passing it."""

from __future__ import annotations

import click
import pytest

from ginstand.cli.main import cli
from ginstand.tools.check_help import command_names, findings, walk


def test_every_command_and_option_has_help() -> None:
    assert list(findings()) == []


def test_the_walk_reaches_the_nested_commands() -> None:
    names = [name for name, _ in walk(cli)]
    assert "cli producer add" in names
    assert "cli run press" in names
    assert "cli settle statement" in names


def test_the_listing_comes_off_the_parser() -> None:
    names = command_names()
    assert "cli init" in names
    assert "cli yard receive" in names
    assert not any(isinstance(cli.commands.get(name), click.Group) for name in names)


def test_no_command_name_carries_an_underscore() -> None:
    for name, command in walk(cli):
        assert command.name is None or "_" not in command.name, name


def test_every_group_the_line_offers_is_reachable() -> None:
    groups = {name for name, command in walk(cli) if isinstance(command, click.Group)}
    for wanted in ("cli producer", "cli run", "cli card", "cli loan", "cli settle"):
        assert wanted in groups


def test_the_command_line_offers_a_useful_number_of_commands() -> None:
    assert len(command_names()) >= 30


def test_a_command_with_no_help_is_reported() -> None:
    """The check has to have been seen to fire, not only to pass."""
    bare = click.Group("root")
    bare.add_command(click.Command("bare"))
    with_underscore = click.Command("with_underscore", help="Does something.")
    bare.add_command(with_underscore)
    without_help = click.Command("silent", help="Says something.", params=[click.Option(["--why"])])
    bare.add_command(without_help)

    messages = []
    for name, command in walk(bare):
        if command is bare:
            continue
        if not (command.help or command.short_help):
            messages.append(f"{name} has no help")
        if command.name and "_" in command.name:
            messages.append(f"{name} has an underscore in its name")
        for parameter in command.params:
            if not getattr(parameter, "help", None):
                messages.append(f"{name} {parameter.opts[0]} has no help")

    assert "root bare has no help" in messages
    assert "root with_underscore has an underscore in its name" in messages
    assert "root silent --why has no help" in messages


def test_the_check_reports_what_the_walk_found() -> None:
    """Fed a group with three defects in it, the check finds all three."""
    bare = click.Group("cli", help="Root.")
    bare.add_command(click.Command("bare"))
    bare.add_command(click.Command("with_underscore", help="Does something."))
    bare.add_command(
        click.Command("silent", help="Says something.", params=[click.Option(["--why"])])
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("ginstand.tools.check_help.cli", bare)
    try:
        messages = [finding.message for finding in findings()]
    finally:
        monkeypatch.undo()
    assert "cli bare has no help" in messages
    assert "cli with_underscore has an underscore in its name" in messages
    assert "cli silent --why has no help" in messages
