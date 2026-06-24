"""The design note describes code that is still there.

A design note is the first document to go stale and the last one anybody
notices has, because nothing breaks when it does. So every module and every name
the note points at is looked up, and the note fails the build when it is
describing something that has moved.

It does not check that the prose is true. Nothing can. It checks that the things
the prose names exist, which is the part that rots on its own.
"""

from __future__ import annotations

import importlib
import re
from collections.abc import Iterator
from types import ModuleType

from ginstand.tools.base import Finding, repo_root, run

DOCUMENT = "docs/design.md"

MODULE = re.compile(r"`(ginstand(?:\.[a-z_]+)+)`")
NAME = re.compile(r"`([a-z_]+)`")


def note() -> str:
    """The design note, read."""
    return (repo_root() / DOCUMENT).read_text()


def paths() -> tuple[str, ...]:
    """Every dotted ginstand path the note points at, in the order it names them."""
    return tuple(dict.fromkeys(MODULE.findall(note())))


def resolves(dotted: str) -> bool:
    """Whether a dotted path names a module, or a name inside one.

    The note points at both. ``ginstand.ginning.shares`` is a module and
    ``ginstand.settle.close.close`` is a function in one, and the note is right
    about both of them, so the check has to handle both.
    """
    try:
        importlib.import_module(dotted)
    except ImportError:
        pass
    else:
        return True
    parent, _, leaf = dotted.rpartition(".")
    if not parent:
        return False
    try:
        module = importlib.import_module(parent)
    except ImportError:
        return False
    return hasattr(module, leaf)


def sections() -> Iterator[tuple[str, str]]:
    """Every section of the note, as its heading and the whole of its text.

    The heading is kept in the text because that is where a section names the
    module it is about, and the names in the body have to be looked for in it.
    """
    for part in re.split(r"^## ", note(), flags=re.MULTILINE)[1:]:
        heading, _, _body = part.partition("\n")
        yield heading.strip(), part


def bare_names(body: str) -> tuple[str, ...]:
    """Every bare name a section mentions, which should be in one of its modules."""
    return tuple(dict.fromkeys(NAME.findall(MODULE.sub(" ", body))))


def _has(module: ModuleType, name: str) -> bool:
    """Whether a module offers a name, at its top level or on a class in it.

    The note names methods as often as it names functions, because a rule that
    hangs off a record is still the rule. ``staple_points`` is a method on
    ``Schedule`` and the note is right to call it by name.
    """
    if hasattr(module, name):
        return True
    return any(
        isinstance(member, type) and hasattr(member, name) for member in vars(module).values()
    )


def findings() -> Iterator[Finding]:
    """Everything the note names that is not there."""
    path = repo_root() / DOCUMENT
    for dotted in paths():
        if not resolves(dotted):
            yield Finding(path, 1, f"{dotted} is not there any more")

    for heading, body in sections():
        here = [dotted for dotted in MODULE.findall(body) if resolves(dotted)]
        modules = []
        for dotted in here:
            try:
                modules.append(importlib.import_module(dotted))
            except ImportError:
                parent, _, _leaf = dotted.rpartition(".")
                modules.append(importlib.import_module(parent))
        if not modules:
            continue
        for name in bare_names(body):
            if not any(_has(module, name) for module in modules):
                yield Finding(path, 1, f"{heading}: {name} is not in {', '.join(here)}")


def main() -> None:
    """Run the check."""
    run("check_design", findings())


if __name__ == "__main__":
    main()
