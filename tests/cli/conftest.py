"""A click runner and a book on disk for the command line tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from ginstand.cli.main import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def book_path(tmp_path: Path) -> Path:
    return tmp_path / "book.sqlite3"


@pytest.fixture
def gin(runner: CliRunner, book_path: Path) -> Callable[..., Result]:
    """Run a command against a book that has already been stood up."""
    runner.invoke(cli, ["--book", str(book_path), "init", "--on", "2025-08-04"])

    def call(*args: str) -> Result:
        return runner.invoke(cli, ["--book", str(book_path), *args])

    return call
