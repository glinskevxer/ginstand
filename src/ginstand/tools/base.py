"""What every check shares: finding the source, reporting, and the exit status."""

from __future__ import annotations

import sys
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path


def source_root() -> Path:
    """The package's own source directory."""
    return Path(__file__).resolve().parent.parent


def repo_root() -> Path:
    """The checkout the package was installed from, or its parent otherwise."""
    return source_root().parent.parent


def source_files(skip: Iterable[str] = ()) -> Iterator[Path]:
    """Every Python file in the package, in path order."""
    skipped = set(skip)
    for path in sorted(source_root().rglob("*.py")):
        if any(part in skipped for part in path.parts):
            continue
        yield path


def suite_files() -> Iterator[Path]:
    """Every Python file in the test suite, in path order."""
    tests = repo_root() / "tests"
    if not tests.is_dir():
        return
    yield from sorted(tests.rglob("*.py"))


def module_name(path: Path) -> str:
    """The dotted module name a source file has."""
    relative = path.relative_to(source_root().parent)
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


@dataclass(frozen=True, slots=True)
class Finding:
    """One thing a check found."""

    path: Path
    line: int
    message: str

    def __str__(self) -> str:
        try:
            shown = self.path.relative_to(repo_root())
        except ValueError:  # pragma: no cover - only when installed elsewhere
            shown = self.path
        return f"{shown}:{self.line}: {self.message}"


def report(name: str, findings: Iterable[Finding]) -> int:
    """Print what a check found and give back its exit status."""
    found = list(findings)
    for finding in found:
        print(finding)
    if found:
        print(f"{name}: {len(found)} problems")
        return 1
    print(f"{name}: clean")
    return 0


def run(name: str, findings: Iterable[Finding]) -> None:
    """Report and exit, for a check being run as a module."""
    sys.exit(report(name, findings))
