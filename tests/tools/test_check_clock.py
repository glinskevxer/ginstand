"""The clock check, and the package passing it."""

from __future__ import annotations

from pathlib import Path

import pytest

from ginstand.tools.check_clock import check_file, findings


def test_nothing_in_the_package_reads_the_clock() -> None:
    assert list(findings()) == []


@pytest.mark.parametrize(
    "line",
    [
        "day = date.today()",
        "stamp = datetime.now()",
        "stamp = datetime.utcnow()",
        "stamp = datetime.today()",
        "at = time.time()",
        "at = time.monotonic()",
    ],
)
def test_a_clock_reading_is_found(tmp_path: Path, line: str) -> None:
    path = tmp_path / "m.py"
    path.write_text(f'"""A module."""\n\n\ndef work():\n    """Work."""\n    {line}\n')
    found = list(check_file(path))
    assert len(found) == 1
    assert "reads the wall clock" in found[0].message


def test_a_bare_today_call_is_found(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text('"""A module."""\n\nx = today()\n')
    assert [f.message for f in check_file(path)] == ["today() reads the wall clock"]


def test_a_day_passed_in_is_clean(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text('"""A module."""\n\n\ndef work(on):\n    """Work."""\n    return on\n')
    assert list(check_file(path)) == []


def test_a_date_built_from_parts_is_clean(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text('"""A module."""\n\nx = date(2025, 10, 14)\n')
    assert list(check_file(path)) == []


def test_a_method_called_today_on_something_else_is_still_found(
    tmp_path: Path,
) -> None:
    path = tmp_path / "m.py"
    path.write_text('"""A module."""\n\nx = date.today()\n')
    assert len(list(check_file(path))) == 1


def test_an_attribute_that_is_not_on_the_list_is_clean(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text('"""A module."""\n\nx = book.today_total()\n')
    assert list(check_file(path)) == []
