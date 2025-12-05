"""Nothing in this package reads the wall clock.

Every operation that needs to know what day it is takes the day as an argument.
That is what makes a settlement reproducible a year later and what lets the
tests run on any day of the year without freezing anything.

It is easy to lose. One convenience default of ``date.today()`` on a report and
the report's output depends on when it was run, which nobody notices until two
people run it on different days and disagree.

The command line is checked too. A default of today on an option is the same
mistake wearing a nicer coat.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

from ginstand.tools.base import Finding, run, source_files

FORBIDDEN = {
    ("date", "today"),
    ("datetime", "today"),
    ("datetime", "now"),
    ("datetime", "utcnow"),
    ("time", "time"),
    ("time", "monotonic"),
    ("time", "perf_counter"),
}
"""Attribute calls that would put the wall clock into a result."""

FORBIDDEN_NAMES = {"today", "utcnow"}
"""Bare names that could only have come from one of the above."""


def check_file(path: Path) -> Iterator[Finding]:
    """Every wall clock reading in one file."""
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
            pair = (target.value.id, target.attr)
            if pair in FORBIDDEN:
                yield Finding(path, node.lineno, f"{pair[0]}.{pair[1]}() reads the wall clock")
        elif isinstance(target, ast.Name) and target.id in FORBIDDEN_NAMES:
            yield Finding(path, node.lineno, f"{target.id}() reads the wall clock")


def findings() -> Iterator[Finding]:
    """Every wall clock reading in the package."""
    for path in source_files():
        yield from check_file(path)


def main() -> None:
    """Run the check."""
    run("check_clock", findings())


if __name__ == "__main__":
    main()
