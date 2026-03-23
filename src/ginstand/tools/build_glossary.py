"""Write the domain glossary out of the code, and check it is still current.

The gin office asks two kinds of question about a word. What does it mean, and
what number is it set to. Both answers are already in the code: the meanings are
the docstrings under the enum members and the constants, and the numbers are the
constants themselves.

So the glossary is generated from the source rather than written beside it. A
hand written one answers the first question and goes stale on the second, which
is the worse half to be wrong about: nobody argues about what micronaire means
and everybody argues about where the premium band starts.

Only documented constants are listed. A constant with no docstring under it is
one nobody outside its own module needs to know about.
"""

from __future__ import annotations

import argparse
import ast
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from ginstand.tools.base import module_name, repo_root, source_files

DOCUMENT = "docs/glossary.md"


@dataclass(frozen=True, slots=True)
class Term:
    """One word the glossary explains."""

    module: str
    name: str
    value: str
    meaning: str


def _docstring_after(body: list[ast.stmt], index: int) -> str:
    if index + 1 >= len(body):
        return ""
    following = body[index + 1]
    if (
        isinstance(following, ast.Expr)
        and isinstance(following.value, ast.Constant)
        and isinstance(following.value.value, str)
    ):
        return " ".join(following.value.value.split())
    return ""


def constants(path: Path) -> Iterator[Term]:
    """Every documented module level constant in one file."""
    tree = ast.parse(path.read_text(), filename=str(path))
    dotted = module_name(path)
    for index, node in enumerate(tree.body):
        target = _assigned_name(node)
        if target is None or not target.isupper():
            continue
        meaning = _docstring_after(tree.body, index)
        if not meaning:
            continue
        yield Term(
            module=dotted,
            name=target,
            value=_value_of(node),
            meaning=meaning,
        )


def _assigned_name(node: ast.stmt) -> str | None:
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        first = node.targets[0]
        if isinstance(first, ast.Name):
            return first.id
    return None


def _value_of(node: ast.stmt) -> str:
    value = node.value if isinstance(node, ast.AnnAssign | ast.Assign) else None
    if value is None:
        return ""
    text = ast.unparse(value)
    return text if len(text) <= 60 else ""


def words(path: Path) -> Iterator[Term]:
    """Every documented enum member in one file."""
    tree = ast.parse(path.read_text(), filename=str(path))
    dotted = module_name(path)
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if not any(
            isinstance(base, ast.Name) and base.id in {"StrEnum", "IntEnum"} for base in node.bases
        ):
            continue
        for index, member in enumerate(node.body):
            name = _assigned_name(member)
            if name is None or not name.isupper():
                continue
            meaning = _docstring_after(node.body, index)
            if not meaning:
                continue
            yield Term(
                module=dotted,
                name=f"{node.name}.{name}",
                value=_value_of(member),
                meaning=meaning,
            )


def terms() -> tuple[Term, ...]:
    """Every term in the package, in module then name order."""
    found: list[Term] = []
    for path in source_files(skip=("tools",)):
        found.extend(constants(path))
        found.extend(words(path))
    return tuple(sorted(found, key=lambda term: (term.module, term.name)))


def build() -> str:
    """The glossary, read off the source."""
    lines = [
        "# Glossary",
        "",
        "This file is generated. Run `python -m ginstand.tools.build_glossary`",
        "after adding or changing a documented constant, and CI will tell you if",
        "you forgot.",
        "",
    ]
    current = ""
    for term in terms():
        if term.module != current:
            current = term.module
            lines.extend(["", f"## {current}", ""])
        value = f" = `{term.value}`" if term.value else ""
        lines.append(f"**{term.name}**{value}")
        lines.extend(["", term.meaning, ""])
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    """Write the glossary, or check the one on disk still matches."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="do not write, compare")
    args = parser.parse_args()

    path = repo_root() / DOCUMENT
    wanted = build()
    if not args.check:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(wanted)
        print(f"build_glossary: wrote {DOCUMENT} with {len(terms())} terms")
        return
    if not path.is_file():
        print(f"build_glossary: {DOCUMENT} is not there, run this without --check")
        sys.exit(1)
    if path.read_text() != wanted:
        print(f"build_glossary: {DOCUMENT} is out of date, run this without --check")
        sys.exit(1)
    print("build_glossary: clean")


if __name__ == "__main__":
    main()
