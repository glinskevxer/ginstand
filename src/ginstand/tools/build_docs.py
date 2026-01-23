"""Write the command reference out of the parser, and check it is still current.

The reference is generated because a hand written one goes stale the first time
somebody adds an option, and a stale reference is worse than none: people trust
it. Generating it means the only way to change the documentation is to change
the command, which is the right way round.

Like the schema, CI checks the file on disk still matches, so forgetting to
regenerate fails the build rather than shipping.
"""

from __future__ import annotations

import argparse
import sys

import click

from ginstand.cli.main import cli
from ginstand.tools.base import repo_root
from ginstand.tools.check_help import walk

DOCUMENT = "docs/commands.md"


def _usage(name: str, command: click.Command) -> str:
    words = name.split()[1:]
    parts = ["ginstand", *words]
    for parameter in command.params:
        if isinstance(parameter, click.Argument):
            label = parameter.name or "value"
            if parameter.nargs == -1:
                parts.append(f"<{label}>...")
            elif parameter.required:
                parts.append(f"<{label}>")
            else:
                parts.append(f"[{label}]")
    return " ".join(parts)


def _options(command: click.Command) -> list[str]:
    rows = []
    for parameter in command.params:
        if isinstance(parameter, click.Argument):
            continue
        flags = ", ".join(f"`{flag}`" for flag in parameter.opts)
        help_text = getattr(parameter, "help", "") or ""
        required = " (required)" if parameter.required else ""
        rows.append(f"- {flags} — {help_text}{required}")
    return rows


def build() -> str:
    """The command reference, read off the parser."""
    lines = [
        "# Commands",
        "",
        "This file is generated. Run `python -m ginstand.tools.build_docs` after",
        "changing a command, and CI will tell you if you forgot.",
        "",
        "Every command takes `--book` on the top level command, and every command",
        "that needs a date takes it as an argument. Nothing reads the clock.",
        "",
    ]
    for name, command in walk(cli):
        if command is cli:
            continue
        words = name.split()[1:]
        depth = "#" * (len(words) + 1)
        lines.append(f"{depth} {' '.join(words)}")
        lines.append("")
        summary = (command.help or command.short_help or "").strip().splitlines()
        if summary:
            lines.extend([summary[0], ""])
        if not isinstance(command, click.Group):
            lines.extend(["```", _usage(name, command), "```", ""])
            options = _options(command)
            if options:
                lines.extend([*options, ""])
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    """Write the reference, or check the one on disk still matches."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="do not write, compare")
    args = parser.parse_args()

    path = repo_root() / DOCUMENT
    wanted = build()
    if not args.check:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(wanted)
        print(f"build_docs: wrote {DOCUMENT}")
        return
    if not path.is_file():
        print(f"build_docs: {DOCUMENT} is not there, run this without --check")
        sys.exit(1)
    if path.read_text() != wanted:
        print(f"build_docs: {DOCUMENT} is out of date, run this without --check")
        sys.exit(1)
    print("build_docs: clean")


if __name__ == "__main__":
    main()
