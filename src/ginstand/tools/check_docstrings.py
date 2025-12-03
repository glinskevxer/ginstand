"""Every public module, class and function carries a docstring.

Only what a module actually offers is checked: its own docstring, and the
classes and functions defined at module level or in a class body. A function
defined inside another function is a local, not a surface, and the command line
is full of them.

Private names are exempt, and so are the few dunder methods this package writes
whose meaning is fixed by the language. Everything else is documented because
the docstring is where the reason lives, and this package's reasons are not
recoverable from its code.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

from ginstand.tools.base import Finding, run, source_files

EXEMPT_NAMES = {"__post_init__", "__str__", "__enter__", "__exit__", "__len__"}


def _public(name: str) -> bool:
    return not name.startswith("_")


def _surface(body: list[ast.stmt]) -> Iterator[ast.stmt]:
    """The definitions a module or a class offers, one level deep."""
    for node in body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            yield node
        elif isinstance(node, ast.ClassDef):
            yield node
            yield from _surface(node.body)


def check_file(path: Path) -> Iterator[Finding]:
    """Every public definition in one file that has no docstring."""
    tree = ast.parse(path.read_text(), filename=str(path))
    if ast.get_docstring(tree) is None:
        yield Finding(path, 1, "the module has no docstring")
    for node in _surface(tree.body):
        name = node.name  # type: ignore[attr-defined]
        if name in EXEMPT_NAMES or not _public(name):
            continue
        if ast.get_docstring(node) is None:  # type: ignore[arg-type]
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            yield Finding(path, node.lineno, f"{kind} {name} has no docstring")


def findings() -> Iterator[Finding]:
    """Everything undocumented across the package."""
    for path in source_files():
        yield from check_file(path)


def main() -> None:
    """Run the check."""
    run("check_docstrings", findings())


if __name__ == "__main__":
    main()
