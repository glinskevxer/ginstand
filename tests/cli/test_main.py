"""The entry point, and the two commands that stand a book up."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from click.testing import CliRunner, Result

from ginstand import __version__
from ginstand.cli.main import cli
from ginstand.store.migrations import latest_version


def test_the_version_prints_on_its_own(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_init_stands_a_book_up(runner: CliRunner, book_path: Path) -> None:
    result = runner.invoke(cli, ["--book", str(book_path), "init", "--on", "2025-08-04"])
    assert result.exit_code == 0
    assert f"schema version {latest_version()}" in result.output
    assert book_path.exists()


def test_init_refuses_a_book_that_is_already_there(runner: CliRunner, book_path: Path) -> None:
    runner.invoke(cli, ["--book", str(book_path), "init", "--on", "2025-08-04"])
    result = runner.invoke(cli, ["--book", str(book_path), "init", "--on", "2025-08-04"])
    assert result.exit_code != 0
    assert "already there" in result.output


def test_a_command_against_a_book_that_is_not_there_says_so(
    runner: CliRunner, book_path: Path
) -> None:
    result = runner.invoke(cli, ["--book", str(book_path), "about"])
    assert result.exit_code != 0
    assert "there is no book at" in result.output


def test_opening_a_missing_book_does_not_create_a_file(runner: CliRunner, book_path: Path) -> None:
    runner.invoke(cli, ["--book", str(book_path), "about"])
    assert not book_path.exists()


def test_about_says_what_the_book_holds(gin: Callable[..., Result]) -> None:
    result = gin("about")
    assert result.exit_code == 0
    assert f"ginstand {__version__}" in result.output
    assert "0 producers, 0 modules, 0 bales" in result.output


def test_a_date_in_the_wrong_order_is_refused_before_anything_is_written(
    runner: CliRunner, book_path: Path
) -> None:
    result = runner.invoke(cli, ["--book", str(book_path), "init", "--on", "04/08/2025"])
    assert result.exit_code != 0
    assert "ISO date" in result.output
    assert not book_path.exists()


def test_the_group_help_lists_the_commands(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.output
    assert "about" in result.output
