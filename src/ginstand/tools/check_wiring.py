"""Every module is reachable from the command line.

A module with green tests and nothing calling it is code that is only exercised
where it is defined. It passes, it stays passing, and it is not doing anything.
That has happened here: a rule was written, tested, and then the command that
was going to use it was written a different way.

So the import graph is walked from the entry point, and anything not reached is
reported. The checks themselves are the exception, because they are run by CI
rather than by the command line.

Two things about the graph are worth knowing, because getting either wrong makes
the whole package look unreachable. ``from ginstand.cli import growers`` imports
a module, not a name, so the target is ``ginstand.cli.growers`` and not
``ginstand.cli``. And importing anything imports its parent packages, so
reaching ``ginstand.units.weight`` reaches ``ginstand.units`` too.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from functools import cache
from pathlib import Path

from ginstand.tools.base import Finding, module_name, run, source_files

ENTRY = "ginstand.cli.main"

EXEMPT = {"ginstand", "ginstand.tools"}
"""The package itself, and the checks, which CI runs rather than the office."""


@cache
def _graph() -> dict[str, frozenset[str]]:
    graph: dict[str, frozenset[str]] = {}
    for path in source_files():
        graph[module_name(path)] = frozenset(_imports_of(path))
    return graph


def _imports_of(path: Path) -> Iterator[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("ginstand"):
                    yield alias.name
        elif (
            isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("ginstand")
        ):
            yield node.module
            for alias in node.names:
                yield f"{node.module}.{alias.name}"


def _parents(dotted: str) -> Iterator[str]:
    """Every package that importing ``dotted`` also imports."""
    parts = dotted.split(".")
    for depth in range(1, len(parts)):
        yield ".".join(parts[:depth])


def reachable(entry: str = ENTRY) -> frozenset[str]:
    """Every module reachable by imports from an entry point."""
    graph = _graph()
    seen: set[str] = set()
    stack = [entry]
    while stack:
        current = stack.pop()
        if current in seen or current not in graph:
            continue
        seen.add(current)
        stack.extend(graph[current])
        stack.extend(_parents(current))
    return frozenset(seen)


def findings() -> Iterator[Finding]:
    """Every module nothing reaches."""
    found = reachable()
    for path in source_files():
        dotted = module_name(path)
        if dotted in EXEMPT or dotted.startswith("ginstand.tools."):
            continue
        if dotted not in found:
            yield Finding(path, 1, f"{dotted} is not reachable from {ENTRY}")


def main() -> None:
    """Run the check."""
    run("check_wiring", findings())


if __name__ == "__main__":
    main()
