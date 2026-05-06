"""Every public name this package defines is used somewhere.

A function nobody calls is not neutral. It is read as working code by the next
person, it shows up in a search, it gets maintained through a refactor, and it
is wrong in some way nobody has found because nothing exercises it.

Names are looked for across the source and the tests, by name rather than by
import graph. That is coarse and it is deliberately coarse: a name used only
through ``getattr`` is still used, and a check that could not see that would
have to be argued with every time somebody wrote one.

Command functions are exempt. Click holds them by decorating them, and nothing
else ever writes their names down.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from ginstand.tools.base import Finding, run, source_files, suite_files

EXEMPT_NAMES = {"main", "run"}
"""Entry points, held by the console script and by being run as a module."""


@dataclass(frozen=True, slots=True)
class Defined:
    """One public name and where it was defined."""

    path: Path
    line: int
    name: str
    decorated: bool


def _decorated(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> bool:
    return bool(node.decorator_list)


def definitions(path: Path) -> Iterator[Defined]:
    """Every public name defined at module level in one file."""
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            if node.name.startswith("_") or node.name in EXEMPT_NAMES:
                continue
            yield Defined(path=path, line=node.lineno, name=node.name, decorated=_decorated(node))


def _uses(name: str, text: str) -> int:
    return len(re.findall(rf"\b{re.escape(name)}\b", text))


def findings() -> Iterator[Finding]:
    """Every public name nothing else mentions."""
    sources = {path: path.read_text() for path in source_files()}
    suite = {path: path.read_text() for path in suite_files()}
    everything = list(sources.items()) + list(suite.items())

    for path, text in sources.items():
        for defined in definitions(path):
            if defined.decorated:
                continue
            uses = sum(_uses(defined.name, body) for other, body in everything if other != path)
            if uses == 0 and _uses(defined.name, text) <= 1:
                yield Finding(path, defined.line, f"{defined.name} is not used anywhere")


def main() -> None:
    """Run the check."""
    run("check_exports", findings())


if __name__ == "__main__":
    main()
