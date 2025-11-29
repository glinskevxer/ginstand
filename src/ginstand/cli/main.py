"""The entry point, and the two commands that stand a book up.

The book path is a group option rather than a per command one, so it reads the
way the office says it: ginstand --book 2025.sqlite3 yard standing.
"""

from __future__ import annotations

from pathlib import Path

import click

from ginstand import __version__
from ginstand.cli.common import DATE, Context, run_command
from ginstand.errors import GinstandError
from ginstand.store.book import Book
from ginstand.store.migrations import latest_version


@click.group()
@click.option(
    "--book",
    "book_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("ginstand.sqlite3"),
    show_default=True,
    help="the sqlite book to work in",
)
@click.version_option(__version__, prog_name="ginstand")
@click.pass_context
def cli(ctx: click.Context, book_path: Path) -> None:
    """Cotton gin office records."""
    if ctx.invoked_subcommand == "init":
        ctx.obj = book_path
        return
    try:
        book = Book.open(book_path)
    except GinstandError as exc:
        raise click.ClickException(str(exc)) from exc
    ctx.obj = Context(book=book, path=book_path)
    ctx.call_on_close(book.close)


@cli.command()
@click.option("--on", type=DATE, required=True, help="the day the book was opened")
@click.pass_context
def init(ctx: click.Context, on: object) -> None:
    """Stand up a new book."""
    path = ctx.obj
    assert isinstance(path, Path)

    def work() -> list[str]:
        book = Book.create(path, on)  # type: ignore[arg-type]
        version = book.schema_version
        book.close()
        return [f"opened {path} at schema version {version}"]

    run_command(work)


@cli.command()
@click.pass_context
def about(ctx: click.Context) -> None:
    """Say what this book is and what version wrote it."""
    from ginstand.cli.common import context

    holder = context(ctx)

    def work() -> list[str]:
        return [
            f"ginstand {__version__}",
            f"book {holder.path}",
            f"schema version {holder.book.schema_version} of {latest_version()}",
            f"{holder.book.producers.count()} producers, "
            f"{holder.book.modules.count()} modules, "
            f"{holder.book.bales.count()} bales",
        ]

    run_command(work)


def _register() -> None:
    """Add every command group to the top level command."""
    from ginstand.cli import classing, gin, growers, land, loan, warehousing
    from ginstand.cli import yard as yard_group

    cli.add_command(growers.producer)
    cli.add_command(growers.lease)
    cli.add_command(land.farm)
    cli.add_command(land.field)
    cli.add_command(yard_group.yard)
    cli.add_command(gin.run)
    cli.add_command(classing.card)
    cli.add_command(loan.loan)
    cli.add_command(warehousing.warehouse)
    cli.add_command(warehousing.receipt)


_register()


def run() -> None:
    """The console script entry point."""
    cli()


if __name__ == "__main__":  # pragma: no cover
    run()
