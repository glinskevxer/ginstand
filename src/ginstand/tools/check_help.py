"""Every command and every option says what it is for.

The command line is the only part of this package a person meets, and its help
is the only documentation most of them will read. So the help is checked the way
the code is: a command with no help is a defect, and so is an option with none.

Command names use dashes, never underscores. A command nobody can type without
looking it up is a command that gets typed wrong.

The listing is read off the parser rather than kept in a file, so an undocumented
command cannot happen and a documented one that does not exist cannot either.
"""

from __future__ import annotations

from collections.abc import Iterator

import click

from ginstand.cli.main import cli
from ginstand.tools.base import Finding, run, source_root

VERSION_OPTIONS = {"--version", "--help"}
"""Options click adds itself, whose help is click's business."""


def walk(command: click.Command, path: str = "") -> Iterator[tuple[str, click.Command]]:
    """Every command in the tree, with the words that reach it."""
    name = f"{path} {command.name}".strip() if command.name else path
    yield name, command
    if isinstance(command, click.Group):
        for child in command.commands.values():
            yield from walk(child, name)


def findings() -> Iterator[Finding]:
    """Everything on the command line with no help on it."""
    path = source_root() / "cli" / "main.py"
    for name, command in walk(cli):
        if command is cli:
            continue
        if not (command.help or command.short_help):
            yield Finding(path, 1, f"{name} has no help")
        if command.name and "_" in command.name:
            yield Finding(path, 1, f"{name} has an underscore in its name")
        for parameter in command.params:
            if isinstance(parameter, click.Argument):
                continue
            flags = set(parameter.opts)
            if flags & VERSION_OPTIONS:
                continue
            if not getattr(parameter, "help", None):
                yield Finding(path, 1, f"{name} {parameter.opts[0]} has no help")


def command_names() -> tuple[str, ...]:
    """Every command the line offers, in the order the parser holds them."""
    return tuple(
        name
        for name, command in walk(cli)
        if command is not cli and not isinstance(command, click.Group)
    )


def main() -> None:
    """Run the check."""
    run("check_help", findings())


if __name__ == "__main__":
    main()
