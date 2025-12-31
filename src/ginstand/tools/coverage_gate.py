"""Coverage has to clear a floor, and so does every file on its own.

A single total hides the file that has no tests at all. A package can sit at
ninety five percent with one module at nine, and the module at nine is always the
one that just got written. So there are two floors and the per file one is the
one that catches things.

The report is read out of coverage's own json rather than re-measured, because
this runs after the suite and re-running it to check it would double the time
for nothing.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from ginstand.tools.base import repo_root

DEFAULT_REPORT = "coverage.json"


@dataclass(frozen=True, slots=True)
class FileCoverage:
    """One file's coverage, as the json reports it."""

    path: str
    percent: float
    missing: int


def read_report(path: Path) -> tuple[float, tuple[FileCoverage, ...]]:
    """The total and the per file figures out of a coverage json report."""
    data = json.loads(path.read_text())
    total = float(data["totals"]["percent_covered"])
    files = tuple(
        FileCoverage(
            path=name,
            percent=float(summary["summary"]["percent_covered"]),
            missing=int(summary["summary"]["missing_lines"]),
        )
        for name, summary in sorted(data["files"].items())
    )
    return total, files


def failures(
    total: float, files: tuple[FileCoverage, ...], floor: float, file_floor: float
) -> Iterator[str]:
    """Every floor the report does not clear."""
    if total < floor:
        yield f"coverage is {total:.2f}% and the floor is {floor:.2f}%"
    for item in files:
        if item.percent < file_floor:
            yield (
                f"{item.path} is {item.percent:.2f}% with {item.missing} lines "
                f"uncovered, and the file floor is {file_floor:.2f}%"
            )


def main() -> None:
    """Read the report and hold it to both floors."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--floor", type=float, default=90.0)
    parser.add_argument("--file-floor", type=float, default=70.0)
    parser.add_argument("--report", default=DEFAULT_REPORT)
    args = parser.parse_args()

    path = Path(args.report)
    if not path.is_absolute():
        path = repo_root() / path
    if not path.is_file():
        print(f"coverage_gate: there is no report at {path}")
        sys.exit(1)

    total, files = read_report(path)
    problems = list(failures(total, files, args.floor, args.file_floor))
    for problem in problems:
        print(problem)
    if problems:
        print(f"coverage_gate: {len(problems)} problems")
        sys.exit(1)
    print(f"coverage_gate: clean at {total:.2f}% over {len(files)} files")


if __name__ == "__main__":
    main()
