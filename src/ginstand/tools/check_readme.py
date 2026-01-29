"""Every command the readme shows is a command that exists.

A readme is the first thing anybody runs and the last thing anybody updates. The
commands in it get copied and pasted, so one that has been renamed does not read
as out of date, it reads as broken software.

Every ``ginstand ...`` line in the readme is parsed against the real command
tree, and every check the readme says it runs has to be a module that is there.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

import click

from ginstand.cli.main import cli
from ginstand.tools.base import Finding, repo_root, run, source_root

COMMAND = re.compile(r"^ginstand\s+(.*)$")
CHECK = re.compile(r"^python -m ginstand\.tools\.([a-z_]+)")


def readme_lines() -> list[str]:
    """The readme, one line at a time, with continuations joined up."""
    text = (repo_root() / "README.md").read_text()
    joined = text.replace("\\\n", " ")
    return [line.strip() for line in joined.splitlines()]


def _words(line: str) -> list[str]:
    words = []
    for word in line.split():
        if word.startswith(("-", "<", '"')):
            break
        words.append(word)
    return words


def _resolve(words: list[str]) -> str | None:
    """The command path the readme names that does not exist, or None.

    Walking stops at the first thing that is not a group, because everything
    after a command's own name is an argument rather than a subcommand.
    """
    command: click.Command = cli
    walked: list[str] = []
    for word in words:
        if not isinstance(command, click.Group):
            return None
        found = command.commands.get(word)
        if found is None:
            return " ".join([*walked, word])
        command = found
        walked.append(word)
    return None


def findings() -> Iterator[Finding]:
    """Every command or check the readme names that is not there."""
    path = repo_root() / "README.md"
    for number, line in enumerate(readme_lines(), start=1):
        match = COMMAND.match(line)
        if match:
            rest = match.group(1)
            if rest.startswith("--book"):
                rest = rest.split(None, 2)[2] if len(rest.split(None, 2)) > 2 else ""
            words = _words(rest)
            if not words:
                continue
            missing = _resolve(words)
            if missing:
                yield Finding(path, number, f"there is no command {missing!r}")
        check = CHECK.match(line)
        if check:
            name = check.group(1)
            if not (source_root() / "tools" / f"{name}.py").is_file():
                yield Finding(path, number, f"there is no check called {name}")


def main() -> None:
    """Run the check."""
    run("check_readme", findings())


if __name__ == "__main__":
    main()
