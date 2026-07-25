"""The pieces every command group shares."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from ginstand.cli.common import (
    DATE,
    NUMBER,
    Context,
    context,
    echo_lines,
    run_checked,
    run_command,
)
from ginstand.errors import ValidationError
from ginstand.store.book import Book


def test_a_date_reads_off_the_command_line() -> None:
    assert DATE.convert("2025-10-14", None, None) == date(2025, 10, 14)
    assert DATE.convert(date(2025, 10, 14), None, None) == date(2025, 10, 14)


def test_a_date_in_any_other_order_fails_the_parameter() -> None:
    @click.command()
    @click.option("--on", type=DATE)
    def command(on: date) -> None:
        click.echo(str(on))

    result = CliRunner().invoke(command, ["--on", "14/10/2025"])
    assert result.exit_code != 0
    assert "ISO date" in result.output


def test_a_number_keeps_every_place_that_was_typed() -> None:
    assert NUMBER.convert("78.40", None, None) == Decimal("78.40")
    assert str(NUMBER.convert("78.40", None, None)) == "78.40"
    assert NUMBER.convert(Decimal("1.5"), None, None) == Decimal("1.5")


def test_something_that_is_not_a_number_fails_the_parameter() -> None:
    @click.command()
    @click.option("--acres", type=NUMBER)
    def command(acres: Decimal) -> None:
        click.echo(str(acres))

    result = CliRunner().invoke(command, ["--acres", "lots"])
    assert result.exit_code != 0
    assert "is not a number" in result.output


def test_lines_are_echoed_one_per_line(capsys: pytest.CaptureFixture[str]) -> None:
    echo_lines(["one", "two"])
    assert capsys.readouterr().out == "one\ntwo\n"


def test_our_errors_become_one_printed_line() -> None:
    @click.command()
    def command() -> None:
        def work() -> list[str]:
            raise ValidationError("moisture", "is not a number")

        run_command(work)

    result = CliRunner().invoke(command, [])
    assert result.exit_code != 0
    assert "moisture: is not a number" in result.output
    assert "Traceback" not in result.output


def test_an_error_that_is_not_ours_is_left_alone() -> None:
    @click.command()
    def command() -> None:
        def work() -> list[str]:
            raise ZeroDivisionError("this is a bug")

        run_command(work)

    result = CliRunner().invoke(command, [])
    assert result.exit_code != 0
    assert isinstance(result.exception, ZeroDivisionError)


def test_the_context_carries_the_book_and_its_path(tmp_path: Path) -> None:
    path = tmp_path / "book.sqlite3"
    with Book.create(path, date(2025, 8, 4)) as book:
        holder = Context(book=book, path=path)
        assert holder.book is book
        assert holder.path == path


def test_the_context_is_found_off_the_click_context(tmp_path: Path) -> None:
    path = tmp_path / "book.sqlite3"
    with Book.create(path, date(2025, 8, 4)) as book:
        ctx = click.Context(click.Command("x"))
        ctx.obj = Context(book=book, path=path)
        assert context(ctx).path == path


def test_a_checked_command_prints_and_exits_zero_when_it_is_sound() -> None:
    @click.command()
    def command() -> None:
        run_checked(lambda: (("all well",), True))

    result = CliRunner().invoke(command, [])
    assert result.exit_code == 0
    assert "all well" in result.output


def test_a_checked_command_exits_one_when_it_is_not() -> None:
    @click.command()
    def command() -> None:
        run_checked(lambda: (("something is wrong",), False))

    result = CliRunner().invoke(command, [])
    assert result.exit_code == 1
    assert "something is wrong" in result.output


def test_the_quiet_form_prints_nothing_when_there_is_nothing_wrong() -> None:
    @click.command()
    def command() -> None:
        run_checked(lambda: (("all well",), True), quiet=True)

    result = CliRunner().invoke(command, [])
    assert result.exit_code == 0
    assert result.output == ""


def test_the_quiet_form_still_prints_when_something_is_wrong() -> None:
    @click.command()
    def command() -> None:
        run_checked(lambda: (("something is wrong",), False), quiet=True)

    result = CliRunner().invoke(command, [])
    assert result.exit_code == 1
    assert "something is wrong" in result.output


def test_a_checked_command_turns_our_errors_into_one_line() -> None:
    @click.command()
    def command() -> None:
        def work() -> tuple[tuple[str, ...], bool]:
            raise ValidationError("moisture", "is not a number")

        run_checked(work)

    result = CliRunner().invoke(command, [])
    assert result.exit_code != 0
    assert "moisture: is not a number" in result.output
    assert "Traceback" not in result.output
