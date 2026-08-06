"""The version agrees with itself, and the changelog knows about it.

Three places carry the version and they drift. The package says one thing, the
project file says another, and the changelog has no entry for either. None of
that breaks anything until somebody tries to work out which version a bug report
is against.

The generated documents are checked here too, and only for being present. Their
own checks say whether they are current; this says whether a release would ship
without them, which is a different failure and one that only shows up in the
sdist.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterator

from ginstand import __version__
from ginstand.tools.base import Finding, repo_root, run, source_root

VERSION = re.compile(r"^\d+\.\d+\.\d+$")
CHANGELOG = "CHANGELOG.md"

SHIPPED = ("README.md", "CHANGELOG.md", "constraints.txt")
"""Files a release is not a release without."""

GENERATED = ("docs/commands.md", "docs/schema.md", "docs/glossary.md", "docs/design.md")
"""The documents the checks keep current, which have to be there to be current."""

MINIMUM_NOTES = 3
"""Lines under the newest heading. A release with nothing said about it is one."""


def project_version() -> str:
    """The version the project file declares."""
    data = tomllib.loads((repo_root() / "pyproject.toml").read_text())
    return str(data["project"]["version"])


def changelog_versions() -> tuple[str, ...]:
    """Every version the changelog has a heading for, newest first."""
    text = (repo_root() / CHANGELOG).read_text()
    return tuple(re.findall(r"^## (\d+\.\d+\.\d+)$", text, flags=re.MULTILINE))


def newest_notes() -> tuple[str, ...]:
    """The lines under the newest version heading, blank ones dropped."""
    text = (repo_root() / CHANGELOG).read_text()
    parts = re.split(r"^## \d+\.\d+\.\d+$", text, flags=re.MULTILINE)
    if len(parts) < 2:
        return ()
    return tuple(line for line in parts[1].splitlines() if line.strip())


def missing_files() -> tuple[str, ...]:
    """Every file a release needs that is not there."""
    return tuple(name for name in (*SHIPPED, *GENERATED) if not (repo_root() / name).is_file())


def findings() -> Iterator[Finding]:
    """Everything about the version that does not line up."""
    init = source_root() / "__init__.py"
    project = repo_root() / "pyproject.toml"
    changelog = repo_root() / CHANGELOG

    if not VERSION.match(__version__):
        yield Finding(init, 1, f"{__version__} is not three numbers")
    declared = project_version()
    if declared != __version__:
        yield Finding(project, 1, f"the project says {declared} and the package says {__version__}")
    versions = changelog_versions()
    if not versions:
        yield Finding(changelog, 1, "has no version headings in it")
    elif __version__ not in versions:
        yield Finding(changelog, 1, f"has no entry for {__version__}")
    elif versions[0] != __version__:
        yield Finding(changelog, 1, f"leads with {versions[0]} and the package is {__version__}")
    if len(set(versions)) != len(versions):
        yield Finding(changelog, 1, "has the same version twice")
    notes = newest_notes()
    if versions and len(notes) < MINIMUM_NOTES:
        yield Finding(
            changelog,
            1,
            f"says {len(notes)} lines about {versions[0]}, which is not a release note",
        )
    for name in missing_files():
        yield Finding(repo_root() / name, 1, "is not there, and a release needs it")


def main() -> None:
    """Run the check."""
    run("release_check", findings())


if __name__ == "__main__":
    main()
