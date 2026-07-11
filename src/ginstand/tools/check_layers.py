"""The package's layers point one way.

Seven layers, and a module may only import from its own layer or a lower one.
The point is not tidiness. It is that a rule about cotton must not be reachable
from a rule about how a table prints, because the day it is, the way a report
lays out starts deciding what a producer is paid.

The layers, lowest first:

1. scalars and identifiers, which know nothing about cotton
2. the grade vocabulary and the records
3. the book
4. the rules: yard, ginning, classing, loan, charges, warehouse, quality,
   settle
5. the reports
6. the command line
7. these checks

A module with no layer is a mistake in this file rather than in the package, so
an unplaced module is reported as one.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

from ginstand.tools.base import Finding, module_name, run, source_files

LAYERS: dict[str, int] = {
    "errors": 1,
    "ids": 1,
    "season": 1,
    "units": 1,
    "grades": 2,
    "model": 2,
    "store": 3,
    "yard": 4,
    "ginning": 4,
    "classing": 4,
    "loan": 4,
    "charges": 4,
    "warehouse": 4,
    "settle": 4,
    "quality": 4,
    "invariants": 4,
    "report": 5,
    "cli": 6,
    "tools": 7,
}

ROOT_MODULES = {"errors", "ids", "season", "invariants"}
"""The modules that sit at the package root rather than in a subpackage."""


def layer_of(dotted: str) -> int | None:
    """Which layer a dotted module name belongs to."""
    parts = dotted.split(".")
    if len(parts) < 2:
        return 1
    return LAYERS.get(parts[1])


def imported_modules(path: Path) -> Iterator[tuple[str, int]]:
    """Every ginstand module a file imports, with the line it was imported on."""
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("ginstand"):
                    yield alias.name, node.lineno
        elif (
            isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("ginstand")
        ):
            yield node.module, node.lineno


def check_file(path: Path) -> Iterator[Finding]:
    """Every import in one file that points upwards."""
    dotted = module_name(path)
    mine = layer_of(dotted)
    if mine is None:
        yield Finding(path, 1, f"{dotted} is not placed in a layer")
        return
    for imported, line in imported_modules(path):
        theirs = layer_of(imported)
        if theirs is None:
            yield Finding(path, line, f"{imported} is not placed in a layer")
        elif theirs > mine:
            yield Finding(
                path,
                line,
                f"{dotted} is layer {mine} and imports {imported}, which is layer {theirs}",
            )


def findings() -> Iterator[Finding]:
    """Every upward import in the package."""
    for path in source_files():
        yield from check_file(path)


def main() -> None:
    """Run the check."""
    run("check_layers", findings())


if __name__ == "__main__":
    main()
