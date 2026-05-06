"""The dead code check, and the package passing it."""

from __future__ import annotations

from pathlib import Path

from ginstand.tools.base import source_root
from ginstand.tools.check_exports import EXEMPT_NAMES, definitions, findings


def test_nothing_public_in_the_package_is_unused() -> None:
    assert list(findings()) == []


def test_the_public_names_of_a_file_are_found(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text(
        '"""A module."""\n\n\ndef work():\n    """Work."""\n\n\ndef _helper():\n'
        '    """Help."""\n\n\nclass Thing:\n    """A thing."""\n'
    )
    assert [item.name for item in definitions(path)] == ["work", "Thing"]


def test_a_private_name_is_not_public(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text('"""A module."""\n\n\ndef _work():\n    """Work."""\n')
    assert list(definitions(path)) == []


def test_a_nested_definition_is_not_module_level(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text(
        '"""A module."""\n\n\ndef outer():\n    """Outer."""\n\n    def inner():\n        pass\n'
    )
    assert [item.name for item in definitions(path)] == ["outer"]


def test_a_decorated_definition_is_marked(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text(
        '"""A module."""\n\nimport click\n\n\n@click.command()\ndef work():\n    """Work."""\n'
    )
    found = list(definitions(path))
    assert found[0].decorated


def test_the_entry_points_are_exempt() -> None:
    assert "main" in EXEMPT_NAMES
    assert "run" in EXEMPT_NAMES
    path = source_root() / "tools" / "check_exports.py"
    assert "main" not in [item.name for item in definitions(path)]


def test_every_command_module_is_all_decorated() -> None:
    for path in sorted((source_root() / "cli").glob("*.py")):
        if path.name in {"__init__.py", "common.py", "main.py"}:
            continue
        for item in definitions(path):
            assert item.decorated, f"{path.name}:{item.name}"
