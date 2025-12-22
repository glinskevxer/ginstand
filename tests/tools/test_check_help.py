"""The help check, and the command line passing it."""

from __future__ import annotations

import click

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
