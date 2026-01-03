"""Every dependency is pinned, and the closure agrees with the direct pins.

A range is a promise that some future release of somebody else's package will
also be fine, and nobody making that promise has read the code they are making
it about. So every dependency is an exact version, and the transitive closure is
written down beside it.

The two files drift. A direct pin gets bumped in the project file and the
constraints keep the old one, and then CI installs one version and a developer
installs another. This says so.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterator
from pathlib import Path

from ginstand.tools.base import Finding, repo_root, run

PIN = re.compile(r"^([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)$")


def project_file() -> Path:
    """Where the project's own metadata lives."""
    return repo_root() / "pyproject.toml"


def constraints_file() -> Path:
    """Where the transitive closure is written down."""
    return repo_root() / "constraints.txt"


def direct_pins() -> dict[str, str]:
    """Every dependency the project names, with the version it pins."""
    data = tomllib.loads(project_file().read_text())
    project = data["project"]
    wanted: list[str] = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        wanted.extend(extra)
    found: dict[str, str] = {}
    for line in wanted:
        match = PIN.match(line.strip())
        if match:
            found[_normal(match.group(1))] = match.group(2)
    return found


def unpinned() -> Iterator[str]:
    """Every dependency the project names without an exact version."""
    data = tomllib.loads(project_file().read_text())
    project = data["project"]
    wanted: list[str] = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        wanted.extend(extra)
    for line in wanted:
        if not PIN.match(line.strip()):
            yield line


def closure() -> dict[str, str]:
    """Every package the constraints file pins."""
    found: dict[str, str] = {}
    for line in constraints_file().read_text().splitlines():
        text = line.split("#", 1)[0].strip()
        if not text:
            continue
        match = PIN.match(text)
        if match:
            found[_normal(match.group(1))] = match.group(2)
    return found


def _normal(name: str) -> str:
    return name.lower().replace("_", "-")


def findings() -> Iterator[Finding]:
    """Everything unpinned or out of step."""
    project = project_file()
    for line in unpinned():
        yield Finding(project, 1, f"{line} is not pinned to an exact version")

    pins = direct_pins()
    closed = closure()
    constraints = constraints_file()
    for name, version in sorted(pins.items()):
        if name not in closed:
            yield Finding(constraints, 1, f"{name} is pinned in the project and not here")
        elif closed[name] != version:
            yield Finding(
                constraints,
                1,
                f"{name} is {version} in the project and {closed[name]} here",
            )
    for line in constraints_file().read_text().splitlines():
        text = line.split("#", 1)[0].strip()
        if text and not PIN.match(text):
            yield Finding(constraints, 1, f"{text} is not an exact pin")


def main() -> None:
    """Run the check."""
    run("check_pins", findings())


if __name__ == "__main__":
    main()
