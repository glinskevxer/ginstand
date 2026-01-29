"""The version agrees with itself, and the changelog knows about it.

Three places carry the version and they drift. The package says one thing, the
project file says another, and the changelog has no entry for either. None of
that breaks anything until somebody tries to work out which version a bug report
is against.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterator

from ginstand import __version__
from ginstand.tools.base import Finding, repo_root, run, source_root

VERSION = re.compile(r"^\d+\.\d+\.\d+$")
CHANGELOG = "CHANGELOG.md"


def project_version() -> str:
    """The version the project file declares."""
    data = tomllib.loads((repo_root() / "pyproject.toml").read_text())
    return str(data["project"]["version"])


def changelog_versions() -> tuple[str, ...]:
    """Every version the changelog has a heading for, newest first."""
    text = (repo_root() / CHANGELOG).read_text()
    return tuple(re.findall(r"^## (\d+\.\d+\.\d+)$", text, flags=re.MULTILINE))


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


def main() -> None:
    """Run the check."""
    run("release_check", findings())


if __name__ == "__main__":
    main()
