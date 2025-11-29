"""Commands for settlement: statements, the register and the tariff."""

from __future__ import annotations

from datetime import date

import click

from ginstand.charges.published import seed_price_for, tariff_for
from ginstand.cli.common import DATE, context, run_command
from ginstand.report.settlement import producer_page, reconcile, register
from ginstand.report.table import Align, Column, Table
from ginstand.settle.gather import gather_all
from ginstand.units.money import format_money


@click.group()
def settle() -> None:
    """Settlement."""


@settle.command("statement")
@click.argument("run_ref")
@click.argument("producer")
@click.option("--on", type=DATE, required=True, help="the day the statement is issued")
@click.option("--extra", multiple=True, help="an optional charge code to bill")
@click.pass_context
def settle_statement(
    ctx: click.Context, run_ref: str, producer: str, on: date, extra: tuple[str, ...]
) -> None:
    """One producer's statement for one run."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        crop_year = holder.book.runs.get(run_ref).crop_year
        return producer_page(
            holder.book,
            run_ref,
            producer,
            tariff_for(crop_year),
            seed_price_for(crop_year),
            on,
            extras=extra,
        )

    run_command(work)


@settle.command("register")
@click.argument("run_ref")
@click.option("--on", type=DATE, required=True, help="the day the register is run")
@click.pass_context
def settle_register(ctx: click.Context, run_ref: str, on: date) -> None:
    """Every producer on a run, with what they are owed."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        crop_year = holder.book.runs.get(run_ref).crop_year
        return register(
            holder.book, run_ref, tariff_for(crop_year), seed_price_for(crop_year), on
        ).render()

    run_command(work)


@settle.command("check")
@click.argument("run_ref")
@click.option("--on", type=DATE, required=True, help="the day to check at")
@click.pass_context
def settle_check(ctx: click.Context, run_ref: str, on: date) -> None:
    """Check a run's settlement against the run's own figures."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        crop_year = holder.book.runs.get(run_ref).crop_year
        return reconcile(holder.book, run_ref, tariff_for(crop_year), seed_price_for(crop_year), on)

    run_command(work)


@settle.command("shares")
@click.argument("run_ref")
@click.pass_context
def settle_shares(ctx: click.Context, run_ref: str) -> None:
    """What each producer has on a run, before any money is worked out."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        rows = tuple(
            (
                share.producer,
                str(share.modules),
                f"{share.seed_cotton_pounds:,}",
                str(share.bales),
                f"{share.lint_pounds:,}",
                str(len(share.unclassed)),
                ", ".join(share.leases),
            )
            for share in gather_all(holder.book, run_ref)
        )
        return Table(
            title=f"Shares on gin run {run_ref.strip().upper()}",
            columns=(
                Column("producer"),
                Column("modules", Align.RIGHT),
                Column("seed cotton", Align.RIGHT),
                Column("bales", Align.RIGHT),
                Column("lint", Align.RIGHT),
                Column("unclassed", Align.RIGHT),
                Column("leases"),
            ),
            rows=rows,
            empty_note="nobody has cotton on this run",
        ).render()

    run_command(work)


@settle.command("tariff")
@click.option("--crop-year", type=int, required=True, help="which year's rates")
@click.pass_context
def settle_tariff(ctx: click.Context, crop_year: int) -> None:
    """The published ginning tariff for a crop year."""
    context(ctx)

    def work() -> tuple[str, ...]:
        tariff = tariff_for(crop_year)
        rows = tuple(
            (
                line.code,
                line.description,
                str(line.basis),
                format_money(line.rate),
                "on request" if line.optional else "",
            )
            for line in tariff.lines
        )
        lines = list(
            Table(
                title=f"Ginning tariff, crop year {crop_year}",
                columns=(
                    Column("code"),
                    Column("description"),
                    Column("basis"),
                    Column("rate", Align.RIGHT),
                    Column("when"),
                ),
                rows=rows,
            ).render()
        )
        lines.append("")
        lines.append(f"cottonseed {format_money(seed_price_for(crop_year))} a ton")
        return tuple(lines)

    run_command(work)
