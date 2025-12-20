"""Every source module has a test module against it.

This does not say the tests are good. It says a module was not added without
anybody writing a test file for it, which is the failure this package is
actually prone to: the code gets written with its tests, and then a helper gets
split out into a new module and the tests stay where they were.

The mapping is one to one and mechanical. ``src/ginstand/units/weight.py`` has
``tests/units/test_weight.py``, and a module at the package root has its test at
the root of the suite.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from ginstand.tools.base import Finding, repo_root, run, source_files, source_root


def expected_test(path: Path) -> Path:
    """Where a source module's test file has to be."""
    relative = path.relative_to(source_root())
    return repo_root() / "tests" / relative.parent / f"test_{relative.name}"


def findings() -> Iterator[Finding]:
    """Every module with no test file against it."""
    for path in source_files():
        if path.name == "__init__.py":
            continue
        wanted = expected_test(path)
        if not wanted.is_file():
            shown = wanted.relative_to(repo_root())
            yield Finding(path, 1, f"has no test module at {shown}")


def orphans() -> Iterator[Finding]:
    """Every test module with no source module behind it."""
    tests = repo_root() / "tests"
    for path in sorted(tests.rglob("test_*.py")):
        relative = path.relative_to(tests)
        source = source_root() / relative.parent / relative.name[len("test_") :]
        if not source.is_file():
            yield Finding(path, 1, "tests a module that is not there any more")


def main() -> None:
    """Run the check."""
    run("check_tests", [*findings(), *orphans()])


if __name__ == "__main__":
    main()
