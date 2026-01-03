"""The messages this package raises read the same way.

They are printed straight to a person by the command line, so they are sentences
in a paragraph rather than log lines: lower case at the start, no full stop at
the end, and no mention of the machinery. "no field with reference FL-99" is a
message. "ValidationError: Invalid field." is a stack trace with the traceback
removed.

Only the literal part is checked, and only where the message starts with one.
A message assembled entirely from values has nothing here worth saying about it.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

from ginstand.tools.base import Finding, run, source_files

RAISED = {
    "ValidationError": 1,
    "NotFoundError": None,
    "DuplicateError": None,
    "StateError": 0,
    "ScheduleError": 0,
    "GinstandError": 0,
}
"""Which argument carries the message, or None where the type builds its own."""

MACHINE_WORDS = ("Error", "Exception", "None", "True", "False", "traceback")


def _first_text(node: ast.expr) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        for part in node.values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                return part.value
            return None
    return None


def check_file(path: Path) -> Iterator[Finding]:
    """Every message in one file that does not read the way the others do."""
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
            continue
        func = node.exc.func
        name = func.id if isinstance(func, ast.Name) else None
        if name not in RAISED:
            continue
        index = RAISED[name]
        if index is None or len(node.exc.args) <= index:
            continue
        text = _first_text(node.exc.args[index])
        if text is None or not text:
            continue
        if text[0].isupper():
            yield Finding(path, node.lineno, f"the message starts upper case: {text!r}")
        if text.rstrip().endswith("."):
            yield Finding(path, node.lineno, f"the message ends in a full stop: {text!r}")
        for word in MACHINE_WORDS:
            if word in text:
                yield Finding(path, node.lineno, f"the message names {word}, which is machinery")


def findings() -> Iterator[Finding]:
    """Every message in the package that reads wrong."""
    for path in source_files():
        yield from check_file(path)


def main() -> None:
    """Run the check."""
    run("check_messages", findings())


if __name__ == "__main__":
    main()
