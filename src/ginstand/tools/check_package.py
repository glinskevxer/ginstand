"""The package is shaped so that everything in it actually ships.

Three ways a module gets written and then does not reach anybody. Its directory
has no init file, so the build backend does not see the subpackage. The wheel
configuration names a different directory from the one the code is in. Or the
console script names a function that has been renamed, which nothing notices
until somebody installs it.

None of those fail a test run from a checkout, because a checkout imports from
the source tree and does not care.
"""

from __future__ import annotations

import importlib
import sys
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ginstand.tools.base import Finding, repo_root, run, source_root

STDLIB = set(sys.stdlib_module_names)


def project() -> dict[str, Any]:
    """The project file, read."""
    data: dict[str, Any] = tomllib.loads((repo_root() / "pyproject.toml").read_text())
    return data


def package_directories() -> Iterator[Path]:
    """Every directory inside the package."""
    for path in sorted(source_root().rglob("*")):
        if path.is_dir() and not path.name.startswith((".", "_")):
            yield path


def findings() -> Iterator[Finding]:
    """Everything about the package's shape that would not ship."""
    for directory in package_directories():
        if not (directory / "__init__.py").is_file():
            yield Finding(directory, 1, "is a directory with no __init__.py, so it will not ship")

    tests = repo_root() / "tests"
    for directory in sorted(tests.rglob("*")):
        if (
            directory.is_dir()
            and not directory.name.startswith((".", "_"))
            and not (directory / "__init__.py").is_file()
        ):
            yield Finding(directory, 1, "is a test directory with no __init__.py")

    data = project()
    build = data.get("tool", {})
    wheel = (
        build.get("hatch", {}).get("build", {}).get("targets", {}).get("wheel", {})
        if isinstance(build, dict)
        else {}
    )
    packages = wheel.get("packages", []) if isinstance(wheel, dict) else []
    if packages != ["src/ginstand"]:
        yield Finding(
            repo_root() / "pyproject.toml",
            1,
            f"the wheel packages {packages}, and the code is in src/ginstand",
        )

    scripts = data["project"].get("scripts", {})
    for name, target in scripts.items():
        module, _, function = str(target).partition(":")
        try:
            found = importlib.import_module(module)
        except ImportError:
            yield Finding(repo_root() / "pyproject.toml", 1, f"the {name} script imports {module}")
            continue
        if not callable(getattr(found, function, None)):
            yield Finding(
                repo_root() / "pyproject.toml",
                1,
                f"the {name} script names {target}, which is not a function",
            )

    for path in source_root().glob("*.py"):
        if path.stem in STDLIB and path.stem != "__init__":
            yield Finding(path, 1, f"{path.stem} is the name of a standard library module")


def main() -> None:
    """Run the check."""
    run("check_package", findings())


if __name__ == "__main__":
    main()
