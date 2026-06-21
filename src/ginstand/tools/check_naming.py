"""Test names say what is true, not what is being tested.

A test called ``test_weight`` tells the next person which function it touches
and nothing about what it is claiming. A test called
``test_a_tare_heavier_than_the_gross_reads_as_a_reversed_ticket`` tells them the
rule, and when it fails it tells them the rule is broken without their having to
read it. This package writes the second kind, so a name short enough to be the
first kind is a finding.

The vague words are the ones that survive a rename and mean nothing afterwards.
A test that something "works" was written before anybody decided what working
meant.

"Good" is not on the list, and it was. Good Ordinary and Good Middling are
colour grades, so a check that refused the word would be arguing with the
classing office rather than with the person naming the test.

Module names are checked too, because a file called ``utils`` or ``helpers`` is
a file whose contents nobody has decided on.

And no function in the package itself may be called ``test_``anything. Pytest
collects by name, so a helper called ``test_files`` imported into a test module
is collected as a test and reported as an error rather than as a helper. That
has happened here twice, which is what put the rule in.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from pathlib import Path

from ginstand.tools.base import Finding, run, source_files, suite_files

MINIMUM_WORDS = 4
"""Words in a test name, after the ``test_``. Fewer is a label, not a claim.

Four rather than five, and the difference is not arbitrary. ``days_between_is_
signed`` is four words and it is a claim: it says what is true and it fails
legibly. ``the_check_passes`` is three and it is a label on a function. The line
sits where a clause stops being a clause."""

VAGUE = {
    "works",
    "ok",
    "okay",
    "correct",
    "correctly",
    "basic",
    "simple",
    "stuff",
    "thing",
    "things",
    "bad",
    "valid",
    "invalid",
    "success",
    "failure",
}
"""Words that survive a rename and say nothing afterwards."""

BANNED_MODULES = {"utils", "helpers", "misc", "common_utils", "base_utils", "shared"}
"""Names that mean nobody has decided what is in the file."""

MODULE_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def named_tests(path: Path) -> Iterator[tuple[str, int]]:
    """Every test function in one file, with the line it is on."""
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            yield node.name, node.lineno


def check_test_file(path: Path) -> Iterator[Finding]:
    """Every test name in one file that does not read as a sentence."""
    for name, line in named_tests(path):
        words = name[len("test_") :].split("_")
        if len(words) < MINIMUM_WORDS:
            yield Finding(
                path,
                line,
                f"{name} is {len(words)} words, and a sentence takes {MINIMUM_WORDS}",
            )
        for word in words:
            if word in VAGUE:
                yield Finding(path, line, f"{name} says {word!r}, which means nothing")


def collected_by_pytest() -> Iterator[Finding]:
    """Every function in the package whose name pytest would collect."""
    for path in source_files():
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith(
                "test_"
            ):
                yield Finding(
                    path,
                    node.lineno,
                    f"{node.name} is collected as a test wherever it is imported",
                )


def check_module_names() -> Iterator[Finding]:
    """Every module whose name says nobody decided what is in it."""
    for path in source_files():
        stem = path.stem
        if stem == "__init__":
            continue
        if stem in BANNED_MODULES:
            yield Finding(path, 1, f"{stem} is a name for a file nobody has decided on")
        if not MODULE_NAME.match(stem):
            yield Finding(path, 1, f"{stem} is not a lower case module name")


def findings() -> Iterator[Finding]:
    """Everything named in a way that will not survive being read."""
    yield from check_module_names()
    yield from collected_by_pytest()
    for path in suite_files():
        if path.name.startswith("test_"):
            yield from check_test_file(path)


def main() -> None:
    """Run the check."""
    run("check_naming", findings())


if __name__ == "__main__":
    main()
