"""The layer check, and the package passing it."""

from __future__ import annotations

from pathlib import Path

import pytest

from ginstand.tools.base import source_root
from ginstand.tools.check_layers import (
    LAYERS,
    ROOT_MODULES,
    check_file,
    findings,
    imported_modules,
    layer_of,
)


def test_the_package_layers_point_one_way() -> None:
    assert list(findings()) == []


@pytest.mark.parametrize(
    ("dotted", "layer"),
    [
        ("ginstand.errors", 1),
        ("ginstand.units.weight", 1),
        ("ginstand.model.bale", 2),
        ("ginstand.store.book", 3),
        ("ginstand.loan.value", 4),
        ("ginstand.report.table", 5),
        ("ginstand.cli.main", 6),
        ("ginstand.tools.base", 7),
        ("ginstand", 1),
    ],
)
def test_every_part_of_the_package_has_a_layer(dotted: str, layer: int) -> None:
    assert layer_of(dotted) == layer


def test_a_module_outside_the_map_has_no_layer() -> None:
    assert layer_of("ginstand.somewhere") is None


def test_every_subpackage_on_disk_is_placed() -> None:
    for child in sorted(source_root().iterdir()):
        if child.is_dir() and not child.name.startswith("_"):
            assert child.name in LAYERS
    for name in ROOT_MODULES:
        assert (source_root() / f"{name}.py").is_file()


def test_the_imports_of_a_file_are_found(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text(
        '"""A module."""\n\nimport ginstand.errors\nfrom ginstand.model.bale import Bale\n'
        "import json\nfrom pathlib import Path\n"
    )
    found = dict(imported_modules(path))
    assert set(found) == {"ginstand.errors", "ginstand.model.bale"}


def test_an_upward_import_is_found(tmp_path: Path) -> None:
    path = tmp_path / "bale.py"
    target = source_root() / "model" / "bale.py"
    path.write_text(target.read_text() + "\nfrom ginstand.cli.main import cli\n")
    found = [f for f in check_file(path) if "layer" in f.message]
    assert found
    assert "which is layer 6" in found[0].message


def test_a_downward_import_is_clean(tmp_path: Path) -> None:
    path = source_root() / "loan" / "value.py"
    assert list(check_file(path)) == []


def test_an_import_of_something_unplaced_is_reported(tmp_path: Path) -> None:
    path = tmp_path / "m.py"
    path.write_text('"""A module."""\n\nfrom ginstand.nowhere import thing\n')
    messages = [f.message for f in check_file(path)]
    assert any("is not placed in a layer" in message for message in messages)
