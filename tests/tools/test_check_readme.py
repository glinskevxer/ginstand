"""The readme check, and the readme passing it."""

from __future__ import annotations

from ginstand.tools.check_readme import CHECK, COMMAND, _resolve, findings, readme_lines


def test_the_readme_names_only_commands_that_exist() -> None:
    assert list(findings()) == []


def test_the_readme_is_read_with_its_continuations_joined() -> None:
    lines = readme_lines()
    assert any(line.startswith("ginstand --book") for line in lines)
    assert not any(line.endswith("\\") for line in lines)


def test_a_command_line_is_recognised() -> None:
    assert COMMAND.match("ginstand --book 2025.sqlite3 producer add P-12 x")
    assert not COMMAND.match("pip install -e .")


def test_a_check_line_is_recognised() -> None:
    match = CHECK.match("python -m ginstand.tools.check_clock")
    assert match is not None
    assert match.group(1) == "check_clock"


def test_a_real_command_resolves_to_nothing_missing() -> None:
    assert _resolve(["producer", "add"]) is None
    assert _resolve(["run", "feed-queue"]) is None
    assert _resolve(["about"]) is None


def test_arguments_after_a_command_are_not_walked() -> None:
    assert _resolve(["producer", "add", "P-12", "Aldys"]) is None


def test_a_command_that_does_not_exist_is_named() -> None:
    assert _resolve(["producer", "remove"]) == "producer remove"
    assert _resolve(["nowhere"]) == "nowhere"


def test_the_readme_lists_every_check_ci_runs() -> None:
    text = "\n".join(readme_lines())
    for name in (
        "check_docstrings",
        "check_clock",
        "check_layers",
        "check_migrations",
        "check_tests",
        "check_help",
        "check_wiring",
        "check_pins",
        "check_messages",
    ):
        assert f"python -m ginstand.tools.{name}" in text
