"""The fixture check, and the suite passing it."""

from __future__ import annotations

from pathlib import Path

from ginstand.tools.check_fixtures import OPENERS, check_file, findings

HEADER = '"""Tests."""\n\nimport pytest\n\nfrom ginstand.store.book import Book\n\n\n'


def a_module(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "test_m.py"
    path.write_text(HEADER + body)
    return path


def test_no_fixture_in_the_suite_leaks_a_connection() -> None:
    assert list(findings()) == []


def test_a_fixture_that_returns_an_open_book_is_found(tmp_path: Path) -> None:
    path = a_module(
        tmp_path,
        "@pytest.fixture\ndef stocked():\n    book = Book.create(':memory:', None)\n"
        "    return book\n",
    )
    found = list(check_file(path))
    assert len(found) == 1
    assert "opens a book and never closes it" in found[0].message


def test_a_fixture_that_yields_and_closes_is_clean(tmp_path: Path) -> None:
    path = a_module(
        tmp_path,
        "@pytest.fixture\ndef stocked():\n    book = Book.create(':memory:', None)\n"
        "    try:\n        yield book\n    finally:\n        book.close()\n",
    )
    assert list(check_file(path)) == []


def test_a_fixture_that_uses_a_context_manager_is_clean(tmp_path: Path) -> None:
    path = a_module(
        tmp_path,
        "@pytest.fixture\ndef stocked():\n"
        "    with Book.create(':memory:', None) as book:\n        yield book\n",
    )
    assert list(check_file(path)) == []


def test_a_fixture_that_opens_nothing_is_left_alone(tmp_path: Path) -> None:
    path = a_module(tmp_path, "@pytest.fixture\ndef day():\n    return 1\n")
    assert list(check_file(path)) == []


def test_a_plain_function_that_opens_a_book_is_left_alone(tmp_path: Path) -> None:
    path = a_module(
        tmp_path,
        "def helper():\n    book = Book.create(':memory:', None)\n    return book\n",
    )
    assert list(check_file(path)) == []


def test_a_bare_connect_is_watched_too(tmp_path: Path) -> None:
    path = a_module(
        tmp_path,
        "@pytest.fixture\ndef link():\n    return connect(':memory:')\n",
    )
    assert len(list(check_file(path))) == 1


def test_every_way_of_opening_a_book_is_on_the_list() -> None:
    assert {"create", "open", "open_or_upgrade", "connect"} == OPENERS
