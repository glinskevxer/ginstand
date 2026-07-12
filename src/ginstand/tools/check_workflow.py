"""The CI workflow runs commands that exist and checks that exist.

The walk job gins a season through the installed console script, which is the
only place anything runs the command line end to end. It is also a shell script
inside a YAML file, so nothing type checks it and a renamed command sits there
until a push goes red.

So every ``ginstand`` line in the workflow is parsed against the real command
tree, and every ``python -m ginstand.tools.`` line has to name a check that is
there. And the other way round: every check in the package has to appear in the
workflow, because a check CI does not run is a check that is not running.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

import click

from ginstand.cli.main import cli
from ginstand.tools.base import Finding, repo_root, run, source_root

WORKFLOW = ".github/workflows/ci.yml"

COMMAND = re.compile(r"ginstand\s+--book\s+\S+\s+(.*)$")
CHECK = re.compile(r"python -m ginstand\.tools\.([a-z_]+)")


def workflow_lines() -> list[str]:
    """The workflow, one line at a time, with continuations joined up."""
    text = (repo_root() / WORKFLOW).read_text()
    return [line.strip() for line in text.replace("\\\n", " ").splitlines()]


def _words(rest: str) -> list[str]:
    words = []
    for word in rest.split():
        if word.startswith(("-", '"', "$", "/", "<")):
            break
        words.append(word)
    return words


def missing_command(words: list[str]) -> str | None:
    """The command path the workflow names that does not exist, or None."""
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


def checks_in_the_package() -> tuple[str, ...]:
    """Every check module the package offers, in name order."""
    return tuple(
        sorted(
            path.stem
            for path in (source_root() / "tools").glob("*.py")
            if path.stem.startswith(("check_", "build_"))
            or path.stem in {"smoke", "coverage_gate", "schema_dump", "release_check"}
        )
    )


def checks_in_the_workflow() -> tuple[str, ...]:
    """Every check the workflow runs, in name order."""
    found = set()
    for line in workflow_lines():
        match = CHECK.search(line)
        if match:
            found.add(match.group(1))
    return tuple(sorted(found))


def findings() -> Iterator[Finding]:
    """Everything the workflow names that is not there, and the other way round."""
    path = repo_root() / WORKFLOW
    for number, line in enumerate(workflow_lines(), start=1):
        match = COMMAND.search(line)
        if match:
            words = _words(match.group(1))
            if words:
                missing = missing_command(words)
                if missing:
                    yield Finding(path, number, f"there is no command {missing!r}")
        check = CHECK.search(line)
        if check and not (source_root() / "tools" / f"{check.group(1)}.py").is_file():
            yield Finding(path, number, f"there is no check called {check.group(1)}")

    running = set(checks_in_the_workflow())
    for name in checks_in_the_package():
        if name not in running:
            yield Finding(source_root() / "tools" / f"{name}.py", 1, "is not run by the workflow")


def main() -> None:
    """Run the check."""
    run("check_workflow", findings())


if __name__ == "__main__":
    main()
