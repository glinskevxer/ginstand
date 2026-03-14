"""Commands for settlement: statements, the register and the tariff."""

from __future__ import annotations

from datetime import date

import click

from ginstand.charges.published import seed_price_for, tariff_for
from ginstand.cli.common import DATE, context, parse_amount, run_command
from ginstand.report.settlement import producer_page, reconcile, register
from ginstand.report.table import Align, Column, Table
from ginstand.settle.account import adjust, balance, owing, pay, post_settlement
from ginstand.settle.gather import gather_all
from ginstand.units.money import Money, format_money


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


@click.group()
def account() -> None:
    """The producer account: settlements, adjustments and payments."""


@account.command("post")
@click.argument("run_ref")
@click.argument("producer")
@click.option("--on", type=DATE, required=True, help="the day the settlement is agreed")
@click.option("--extra", multiple=True, help="an optional charge code to bill")
@click.pass_context
def account_post(
    ctx: click.Context, run_ref: str, producer: str, on: date, extra: tuple[str, ...]
) -> None:
    """Agree a statement and put it on the producer's account."""
    holder = context(ctx)

    def work() -> list[str]:
        crop_year = holder.book.runs.get(run_ref).crop_year
        with holder.book.writing() as writing:
            statement, entry = post_settlement(
                writing,
                run_ref,
                producer,
                tariff_for(crop_year),
                seed_price_for(crop_year),
                on,
                extra,
            )
        return [
            f"posted {format_money(entry.amount)} to {entry.producer} for {entry.run}",
            f"balance {format_money(balance(holder.book, entry.producer, crop_year))}",
        ]

    run_command(work)


@account.command("adjust")
@click.argument("producer")
@click.argument("amount")
@click.option("--crop-year", type=int, required=True, help="which crop year")
@click.option("--on", type=DATE, required=True, help="the day the correction is made")
@click.option("--reason", required=True, help="why the account is being corrected")
@click.option("--run", "run_ref", default="", help="the run it relates to, if any")
@click.pass_context
def account_adjust(
    ctx: click.Context,
    producer: str,
    amount: str,
    crop_year: int,
    on: date,
    reason: str,
    run_ref: str,
) -> None:
    """Put a correction on a producer's account."""
    holder = context(ctx)

    def work() -> list[str]:
        with holder.book.writing() as writing:
            entry = adjust(writing, producer, crop_year, parse_amount(amount), on, reason, run_ref)
        return [
            f"adjusted {entry.producer} by {format_money(entry.amount)}: {entry.note}",
            f"balance {format_money(balance(holder.book, entry.producer, crop_year))}",
        ]

    run_command(work)


@account.command("pay")
@click.argument("producer")
@click.argument("amount")
@click.option("--crop-year", type=int, required=True, help="which crop year")
@click.option("--on", type=DATE, required=True, help="the day the money went out")
@click.option("--reference", default="", help="the cheque or transfer reference")
@click.pass_context
def account_pay(
    ctx: click.Context,
    producer: str,
    amount: str,
    crop_year: int,
    on: date,
    reference: str,
) -> None:
    """Record money paid out to a producer."""
    holder = context(ctx)

    def work() -> list[str]:
        with holder.book.writing() as writing:
            entry = pay(writing, producer, crop_year, parse_amount(amount), on, reference)
        return [
            f"paid {format_money(Money(-entry.amount))} to {entry.producer}",
            f"balance {format_money(balance(holder.book, entry.producer, crop_year))}",
        ]

    run_command(work)


@account.command("show")
@click.argument("producer")
@click.option("--crop-year", type=int, required=True, help="which crop year")
@click.pass_context
def account_show(ctx: click.Context, producer: str, crop_year: int) -> None:
    """One producer's account for a crop year."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        who = holder.book.producers.get(producer)
        entries = holder.book.accounts.entries(who.ref, crop_year)
        rows = tuple(
            (
                entry.made.isoformat(),
                str(entry.kind),
                entry.run or entry.reference,
                entry.note,
                format_money(entry.amount),
            )
            for entry in entries
        )
        return Table(
            title=f"Account for {who.ref} {who.name}, crop year {crop_year}",
            columns=(
                Column("date"),
                Column("kind"),
                Column("against"),
                Column("note"),
                Column("amount", Align.RIGHT),
            ),
            rows=rows,
            footers=(
                ("", "", "", "balance", format_money(balance(holder.book, who.ref, crop_year))),
            ),
            empty_note="nothing has been posted to this account",
        ).render()

    run_command(work)


@account.command("owing")
@click.option("--crop-year", type=int, required=True, help="which crop year")
@click.pass_context
def account_owing(ctx: click.Context, crop_year: int) -> None:
    """Every producer with a balance, most owed first."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        found = owing(holder.book, crop_year)
        rows = tuple(
            (producer, holder.book.producers.get(producer).name, format_money(amount))
            for producer, amount in found.items()
        )
        total = Money(sum(found.values()))
        return Table(
            title=f"Balances, crop year {crop_year}",
            columns=(Column("producer"), Column("name"), Column("balance", Align.RIGHT)),
            rows=rows,
            footers=(("", "", format_money(total)),),
            empty_note="every account is square",
        ).render()

    run_command(work)
