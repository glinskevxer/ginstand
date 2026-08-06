"""The release check, and the version lining up."""

from __future__ import annotations

from pathlib import Path

import pytest

from ginstand import __version__
from ginstand.tools.release_check import (
    GENERATED,
    MINIMUM_NOTES,
    VERSION,
    changelog_versions,
    findings,
    main,
    missing_files,
    newest_notes,
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


def test_a_project_version_out_of_step_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The check has to have been seen to fire, not only to pass."""
    monkeypatch.setattr("ginstand.tools.release_check.project_version", lambda: "9.9.9")
    messages = [finding.message for finding in findings()]
    assert any("the project says 9.9.9" in message for message in messages)


def test_a_changelog_with_no_versions_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ginstand.tools.release_check.changelog_versions", tuple)
    assert any("has no version headings" in f.message for f in findings())


def test_a_changelog_with_no_entry_for_this_version_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ginstand.tools.release_check.changelog_versions", lambda: ("0.0.1",))
    assert any("has no entry for" in f.message for f in findings())


def test_a_changelog_that_leads_with_an_older_version_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ginstand.tools.release_check.changelog_versions",
        lambda: ("0.0.1", __version__),
    )
    assert any("leads with 0.0.1" in f.message for f in findings())


def test_a_changelog_with_the_same_version_twice_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ginstand.tools.release_check.changelog_versions",
        lambda: (__version__, __version__),
    )
    assert any("the same version twice" in f.message for f in findings())


def test_a_version_that_is_not_three_numbers_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ginstand.tools.release_check.__version__", "1.0")
    assert any("is not three numbers" in f.message for f in findings())


def test_the_check_exits_non_zero_when_it_finds_something(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("ginstand.tools.release_check.project_version", lambda: "9.9.9")
    with pytest.raises(SystemExit) as exit_info:
        main()
    assert exit_info.value.code == 1
    assert "release_check" in capsys.readouterr().out


def test_the_package_is_at_its_first_full_release() -> None:
    assert __version__ == "1.0.0"


def test_the_changelog_carries_both_releases() -> None:
    assert changelog_versions() == ("1.0.0", "0.1.0")


def test_the_release_notes_say_what_the_checks_found() -> None:
    from ginstand.tools.base import repo_root

    text = (repo_root() / "CHANGELOG.md").read_text()
    assert "colour chart was sitting a layer above" in text
    assert "context manager for its transaction" in text


def test_every_file_a_release_needs_is_there() -> None:
    assert missing_files() == ()


def test_the_generated_documents_are_among_them() -> None:
    assert "docs/commands.md" in GENERATED
    assert "docs/schema.md" in GENERATED
    assert "docs/glossary.md" in GENERATED
    assert "docs/design.md" in GENERATED


def test_the_newest_release_has_something_said_about_it() -> None:
    assert len(newest_notes()) >= MINIMUM_NOTES


def test_a_release_with_nothing_said_about_it_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ginstand.tools.release_check.newest_notes", tuple)
    assert any("which is not a release note" in f.message for f in findings())


def test_a_file_a_release_needs_and_has_not_got_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("ginstand.tools.release_check.missing_files", lambda: ("docs/nowhere.md",))
    assert any("a release needs it" in f.message for f in findings())


def test_a_changelog_with_no_headings_has_no_notes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\nnothing yet\n")
    monkeypatch.setattr("ginstand.tools.release_check.repo_root", lambda: tmp_path)
    assert newest_notes() == ()
