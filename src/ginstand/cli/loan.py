"""Commands for the loan schedule and what bales are worth against it."""

from __future__ import annotations

import click

from ginstand.cli.common import context, run_command
from ginstand.loan.lot import value_lot
from ginstand.loan.schedule import (
    COLOUR_POINTS,
    LEAF_POINTS,
    MICRONAIRE,
    SPOTTED_STAPLE,
    STRENGTH,
    UNIFORMITY,
    WHITE_STAPLE,
    schedule_for,
)
from ginstand.loan.value import value_bale
from ginstand.report.table import Align, Column, Table
from ginstand.units.money import Money, format_money, format_rate


@click.group()
def loan() -> None:
    """The commodity loan schedule."""


@loan.command("value")
@click.argument("tag")
@click.option("--working", is_flag=True, help="print every line of the working")
@click.pass_context
def loan_value(ctx: click.Context, tag: str, working: bool) -> None:
    """What one bale is worth against the loan."""
    holder = context(ctx)

    def work() -> list[str]:
        card = holder.book.cards.get(tag)
        bale = holder.book.bales.get(card.tag)
        owner = holder.book.allocations.owner_of(bale.tag)
        enrolled = holder.book.producers.get(owner).enrolled_for_loan if owner else False
        schedule = schedule_for(bale.crop_year)
        valuation = value_bale(schedule, card, bale.net_pounds, enrolled)
        lines = [valuation.summary]
        if working:
            lines.extend(valuation.working)
        if owner is None:
            lines.append("this bale has not been allocated, so nobody is enrolled for it")
        return lines

    run_command(work)


@loan.command("lot")
@click.argument("producer")
@click.option("--crop-year", type=int, required=True, help="the crop year to value")
@click.pass_context
def loan_lot(ctx: click.Context, producer: str, crop_year: int) -> None:
    """What a producer's classed bales are worth against the loan."""
    holder = context(ctx)

    def work() -> list[str]:
        record = holder.book.producers.get(producer)
        schedule = schedule_for(crop_year)
        priced = []
        for tag in holder.book.allocations.bales_for(record.ref):
            bale = holder.book.bales.get(tag)
            if bale.crop_year != crop_year:
                continue
            card = holder.book.cards.find(tag)
            if card is not None:
                priced.append((card, bale.net_pounds))
        if not priced:
            return [f"{record.ref} has no classed bales in crop year {crop_year}"]
        lot = value_lot(schedule, priced, record.enrolled_for_loan)
        lines = [f"{record.ref}  {record.name}", f"  {lot.line}"]
        if lot.taken:
            lines.append(f"  average {format_rate(lot.average_rate)}")
        for reason, count in sorted(lot.refusals.items()):
            lines.append(f"  {count} refused: {reason}")
        return lines

    run_command(work)


@loan.command("schedule")
@click.option("--crop-year", type=int, required=True, help="which year's tables")
@click.option(
    "--table",
    type=click.Choice(["colour", "leaf", "staple", "mic", "strength", "uniformity"]),
    default="colour",
    show_default=True,
    help="which table to print",
)
@click.pass_context
def loan_schedule(ctx: click.Context, crop_year: int, table: str) -> None:
    """One of the published premium and discount tables."""
    context(ctx)

    def work() -> tuple[str, ...]:
        schedule = schedule_for(crop_year)
        if table == "colour":
            rows = tuple((str(code), str(points)) for code, points in sorted(COLOUR_POINTS.items()))
            return Table(
                title=f"Colour points, crop year {crop_year}"
                f" (base {format_rate(schedule.base_rate)})",
                columns=(Column("code"), Column("points", Align.RIGHT)),
                rows=rows,
            ).render()
        if table == "leaf":
            rows = tuple((str(leaf), str(points)) for leaf, points in sorted(LEAF_POINTS.items()))
            return Table(
                title=f"Leaf points, crop year {crop_year}",
                columns=(Column("leaf"), Column("points", Align.RIGHT)),
                rows=rows,
            ).render()
        ladders = {
            "staple": WHITE_STAPLE,
            "mic": MICRONAIRE,
            "strength": STRENGTH,
            "uniformity": UNIFORMITY,
        }
        ladder = ladders[table]
        band_rows = tuple(
            (str(band.low), str(band.high), str(band.points), band.label) for band in ladder.bands
        )
        lines = list(
            Table(
                title=f"{ladder.name.title()}, crop year {crop_year}",
                columns=(
                    Column("from", Align.RIGHT),
                    Column("to", Align.RIGHT),
                    Column("points", Align.RIGHT),
                    Column("band"),
                ),
                rows=band_rows,
            ).render()
        )
        if table == "staple":
            lines.append("")
            lines.extend(
                Table(
                    title=SPOTTED_STAPLE.name.title(),
                    columns=(
                        Column("from", Align.RIGHT),
                        Column("to", Align.RIGHT),
                        Column("points", Align.RIGHT),
                        Column("band"),
                    ),
                    rows=tuple(
                        (str(band.low), str(band.high), str(band.points), band.label)
                        for band in SPOTTED_STAPLE.bands
                    ),
                ).render()
            )
        return tuple(lines)

    run_command(work)


@loan.command("register")
@click.option("--crop-year", type=int, required=True, help="the crop year to price")
@click.pass_context
def loan_register(ctx: click.Context, crop_year: int) -> None:
    """Every classed bale in a crop year, with what the loan pays."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        schedule = schedule_for(crop_year)
        rows = []
        total = Money(0)
        for card in holder.book.cards.list_all():
            bale = holder.book.bales.get(card.tag)
            if bale.crop_year != crop_year:
                continue
            owner = holder.book.allocations.owner_of(bale.tag)
            enrolled = holder.book.producers.get(owner).enrolled_for_loan if owner else False
            valuation = value_bale(schedule, card, bale.net_pounds, enrolled)
            total = Money(total + valuation.value)
            rows.append(
                (
                    card.tag,
                    owner or "",
                    str(bale.net_pounds),
                    card.summary,
                    format_rate(valuation.rate) if valuation.eligible else "",
                    format_money(valuation.value),
                )
            )
        return Table(
            title=f"Loan register, crop year {crop_year}",
            columns=(
                Column("tag"),
                Column("owner"),
                Column("net", Align.RIGHT),
                Column("classing"),
                Column("rate", Align.RIGHT),
                Column("value", Align.RIGHT),
            ),
            rows=tuple(rows),
            footers=(("", "", "", "", "", format_money(total)),) if rows else (),
            empty_note="nothing has been classed in this crop year",
        ).render()

    run_command(work)
