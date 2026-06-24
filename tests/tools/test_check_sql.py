"""The query check, and the package passing it."""

from __future__ import annotations

from pathlib import Path

import pytest

from ginstand.tools.check_sql import ALLOWED, check_file, findings

HEADER = '"""A module."""\n\n\ndef work(connection, ref):\n    """Work."""\n    '


def a_module(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "m.py"
    path.write_text(HEADER + body + "\n")
    return path


def test_every_query_in_the_package_uses_parameters() -> None:
    assert list(findings()) == []


def test_a_parameterised_query_is_clean(tmp_path: Path) -> None:
    path = a_module(tmp_path, 'connection.execute("SELECT * FROM t WHERE a = ?", (ref,))')
    assert list(check_file(path)) == []


def test_an_interpolated_value_is_found(tmp_path: Path) -> None:
    path = a_module(tmp_path, 'connection.execute(f"SELECT * FROM t WHERE a = {ref}")')
    found = list(check_file(path))
    assert len(found) == 1
    assert "interpolates ref" in found[0].message


def test_an_interpolated_table_name_is_allowed(tmp_path: Path) -> None:
    path = a_module(tmp_path, 'connection.execute(f"SELECT * FROM {self.table}")')
    assert list(check_file(path)) == []


def test_a_query_joined_with_a_plus_is_found(tmp_path: Path) -> None:
    path = a_module(tmp_path, 'connection.execute("SELECT * FROM t WHERE a = " + ref)')
    assert [f.message for f in check_file(path)] == ["the query is built by joining strings"]


def test_a_query_built_with_percent_is_found(tmp_path: Path) -> None:
    path = a_module(tmp_path, 'connection.execute("SELECT * FROM t WHERE a = %s" % ref)')
    assert [f.message for f in check_file(path)] == ["the query is built by joining strings"]


def test_a_query_built_with_format_is_found(tmp_path: Path) -> None:
    path = a_module(tmp_path, 'connection.execute("SELECT {}".format(ref))')
    assert [f.message for f in check_file(path)] == ["the query is built with format()"]


def test_executemany_is_checked_too(tmp_path: Path) -> None:
    path = a_module(tmp_path, 'connection.executemany(f"INSERT INTO t VALUES ({ref})", [])')
    assert len(list(check_file(path))) == 1


def test_a_call_that_is_not_a_query_is_left_alone(tmp_path: Path) -> None:
    path = a_module(tmp_path, 'print(f"hello {ref}")')
    assert list(check_file(path)) == []


def test_a_query_with_no_arguments_is_left_alone(tmp_path: Path) -> None:
    path = a_module(tmp_path, "connection.execute()")
    assert list(check_file(path)) == []


@pytest.mark.parametrize("allowed", sorted(ALLOWED))
def test_every_allowed_interpolation_is_accepted(tmp_path: Path, allowed: str) -> None:
    path = a_module(tmp_path, f'connection.execute(f"SELECT * FROM {{{allowed}}}")')
    assert list(check_file(path)) == []


def test_the_allow_list_is_short_on_purpose() -> None:
    assert len(ALLOWED) <= 10


def test_the_importer_s_column_list_is_on_the_list() -> None:
    assert "names" in ALLOWED
    assert "placeholders" in ALLOWED
