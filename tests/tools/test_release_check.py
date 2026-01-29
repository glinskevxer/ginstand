"""The release check, and the version lining up."""

from __future__ import annotations

from ginstand import __version__
from ginstand.tools.release_check import (
    VERSION,
    changelog_versions,
    findings,
    project_version,
)


def test_the_version_lines_up_everywhere() -> None:
    assert list(findings()) == []


def test_the_package_and_the_project_agree() -> None:
    assert project_version() == __version__


def test_the_version_is_three_numbers() -> None:
    assert VERSION.match(__version__)


def test_the_changelog_leads_with_the_current_version() -> None:
    versions = changelog_versions()
    assert versions
    assert versions[0] == __version__


def test_no_version_appears_twice_in_the_changelog() -> None:
    versions = changelog_versions()
    assert len(set(versions)) == len(versions)


def test_a_version_that_is_not_three_numbers_is_refused() -> None:
    for bad in ("1.0", "1.0.0a1", "v1.0.0", "1.0.0.1"):
        assert not VERSION.match(bad)
