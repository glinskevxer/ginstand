"""The docstring check, and the package passing it."""

from __future__ import annotations

from pathlib import Path

from ginstand.tools.check_docstrings import check_file, findings


def test_the_package_is_documented() -> None:
    assert list(findings()) == []


def test_a_module_with_no_docstring_is_found(tmp_path: Path) -> None:
    path = tmp_path / "bare.py"
    path.write_text("x = 1\n")
    found = list(check_file(path))
    assert len(found) == 1
    assert "the module has no docstring" in found[0].message


def test_an_undocumented_function_is_found(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text('"""A module."""\n\n\ndef work():\n    return 1\n')
    found = list(check_file(path))
    assert [f.message for f in found] == ["function work has no docstring"]


def test_an_undocumented_class_is_found(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text('"""A module."""\n\n\nclass Thing:\n    x = 1\n')
    assert [f.message for f in check_file(path)] == ["class Thing has no docstring"]


def test_a_private_name_is_exempt(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text('"""A module."""\n\n\ndef _work():\n    return 1\n')
    assert list(check_file(path)) == []


def test_the_dunder_methods_this_package_writes_are_exempt(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text(
        '"""A module."""\n\n\nclass Thing:\n    """A thing."""\n\n'
        "    def __str__(self):\n        return ''\n"
    )
    assert list(check_file(path)) == []


def test_a_function_inside_a_function_is_a_local_not_a_surface(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text(
        '"""A module."""\n\n\ndef outer():\n    """Outer."""\n\n'
        "    def inner():\n        return 1\n\n    return inner\n"
    )
    assert list(check_file(path)) == []


def test_a_method_in_a_class_is_still_checked(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text(
        '"""A module."""\n\n\nclass Thing:\n    """A thing."""\n\n'
        "    def work(self):\n        return 1\n"
    )
    assert [f.message for f in check_file(path)] == ["function work has no docstring"]


def test_a_documented_file_is_clean(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text('"""A module."""\n\n\ndef work():\n    """Work."""\n    return 1\n')
    assert list(check_file(path)) == []
