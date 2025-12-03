"""The pieces every command group shares.

The book is opened once, in the group callback, and put on the context. Opening
it per command would mean a typo in a subcommand's arguments still created a
sqlite file, and an empty file where a book should be is worse than an error.

Errors this package raises on purpose are caught at the top and printed as one
line. A traceback in a gin office is not a diagnosis, it is a phone call.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import click

from ginstand.errors import GinstandError
from ginstand.season import parse_date
from ginstand.store.book import Book


@dataclass
class Context:
    """What every command needs: the book and where it came from."""

    book: Book
    path: Path


class DateParam(click.ParamType):
    """A date typed on the command line, ISO only."""

    name = "date"

    def convert(self, value: Any, param: Any, ctx: Any) -> date:
        """Read a date, or fail with the message the season module gave."""
        if isinstance(value, date):
            return value
        try:
            return parse_date(str(value))
        except GinstandError as exc:
            self.fail(str(exc), param, ctx)


class DecimalParam(click.ParamType):
    """A decimal typed on the command line, kept exact."""

    name = "number"

    def convert(self, value: Any, param: Any, ctx: Any) -> Decimal:
        """Read a decimal, keeping every place that was typed."""
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except InvalidOperation:
            self.fail(f"{value!r} is not a number", param, ctx)


DATE = DateParam()
NUMBER = DecimalParam()


def context(ctx: click.Context) -> Context:
    """The context this command group put on the click context."""
    found = ctx.find_object(Context)
    if found is None:  # pragma: no cover - click always fills this in
        raise click.ClickException("no book is open")
    return found


def echo_lines(lines: Iterable[str]) -> None:
    """Print a report's lines."""
    for line in lines:
        click.echo(line)


def run_command(work: Callable[[], Iterable[str]]) -> None:
    """Run a command's body, turning our errors into one printed line."""
    try:
        echo_lines(work())
    except GinstandError as exc:
        raise click.ClickException(str(exc)) from exc
