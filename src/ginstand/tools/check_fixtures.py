"""A test fixture that opens a book closes it.

This check exists because the same defect has now appeared three times, and
every time it was found by running the suite on Python 3.13 rather than by
reading anything.

An unclosed sqlite connection is collected eventually and warns when it is.
Python 3.12 does not raise that warning and 3.13 does, and the suite turns
warnings into errors, so the leak is invisible on one interpreter and fails on
the other. Worse, it fails against whatever test happened to be running when the
collector got round to it, so the report names an innocent test.

The rule: a fixture that opens a book either uses it as a context manager, or
yields it and closes it in a finally. A fixture that returns one has leaked it,
because a fixture's return value is not closed by anything.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

from ginstand.tools.base import Finding, run, suite_files

OPENERS = {"create", "open", "open_or_upgrade", "connect"}
"""Calls that hand back something holding a database connection."""


def _is_fixture(node: ast.FunctionDef) -> bool:
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        name = (
            target.attr
            if isinstance(target, ast.Attribute)
            else target.id
            if isinstance(target, ast.Name)
            else ""
        )
        if name == "fixture":
            return True
    return False


def _opens_a_book(node: ast.AST) -> bool:
    for inner in ast.walk(node):
        if not isinstance(inner, ast.Call):
            continue
        target = inner.func
        if (
            isinstance(target, ast.Attribute)
            and target.attr in OPENERS
            and isinstance(target.value, ast.Name)
            and target.value.id in {"Book", "sqlite3"}
        ):
            return True
        if isinstance(target, ast.Name) and target.id == "connect":
            return True
    return False


def _held_open(node: ast.FunctionDef) -> bool:
    """Whether the fixture takes responsibility for closing what it opened."""
    for inner in ast.walk(node):
        if isinstance(inner, ast.With | ast.AsyncWith):
            return True
        if isinstance(inner, ast.Call):
            target = inner.func
            if isinstance(target, ast.Attribute) and target.attr == "close":
                return True
    return False


def check_file(path: Path) -> Iterator[Finding]:
    """Every fixture in one file that opens a book and does not close it."""
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or not _is_fixture(node):
            continue
        if not _opens_a_book(node):
            continue
        if not _held_open(node):
            yield Finding(
                path,
                node.lineno,
                f"fixture {node.name} opens a book and never closes it",
            )


def findings() -> Iterator[Finding]:
    """Every leaked connection in the suite."""
    for path in suite_files():
        yield from check_file(path)


def main() -> None:
    """Run the check."""
    run("check_fixtures", findings())


if __name__ == "__main__":
    main()
