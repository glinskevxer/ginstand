"""Commands for the module yard."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import click

from ginstand.cli.common import DATE, NUMBER, context, run_command
from ginstand.model.hold import HoldReason
from ginstand.model.module import Module, ModuleKind, WrapKind
from ginstand.report.yard import ginning_queue, holds, standing
from ginstand.units.weight import format_pounds
from ginstand.yard.holds import lift, place, suggest
from ginstand.yard.order import entry_for
from ginstand.yard.receiving import receive


@click.group()
def yard() -> None:
    """The module yard."""


@yard.command("receive")
@click.argument("tag")
@click.option("--field", "field_ref", required=True, help="the field it came off")
@click.option(
    "--kind",
    type=click.Choice([kind.value for kind in ModuleKind]),
    default=ModuleKind.RECTANGULAR.value,
    show_default=True,
    help="how the module was made",
)
@click.option(
    "--wrap",
    type=click.Choice([wrap.value for wrap in WrapKind]),
    default=WrapKind.NONE.value,
    show_default=True,
    help="what is around it",
)
@click.option("--harvested", type=DATE, required=True, help="the day it was picked")
@click.option("--received", type=DATE, required=True, help="the day it crossed the scale")
@click.option("--gross", type=int, required=True, help="gross weight in pounds")
@click.option("--tare", type=int, required=True, help="tare weight in pounds")
@click.option("--moisture", type=NUMBER, required=True, help="moisture percent")
@click.option("--variety", default="", help="the variety, if it differs from the field")
@click.option("--note", default="", help="anything the scale operator wants recorded")
@click.pass_context
def yard_receive(
    ctx: click.Context,
    tag: str,
    field_ref: str,
    kind: str,
    wrap: str,
    harvested: date,
    received: date,
    gross: int,
    tare: int,
    moisture: Decimal,
    variety: str,
    note: str,
) -> None:
    """Weigh a module in."""
    holder = context(ctx)

    def work() -> list[str]:
        module = Module(
            tag=tag,
            field=field_ref,
            kind=ModuleKind(kind),
            harvested=harvested,
            received=received,
            gross_pounds=gross,
            tare_pounds=tare,
            moisture_pct=moisture,
            wrap=WrapKind(wrap),
            variety=variety,
            note=note,
        )
        with holder.book.writing() as writing:
            ticket = receive(writing, module)
        lines = [ticket.line]
        wanted = suggest(module)
        if wanted is not None:
            lines.append(f"suggest holding for {wanted}")
        return lines

    run_command(work)


@yard.command("show")
@click.argument("tag")
@click.option("--on", type=DATE, required=True, help="the day to work the standing out at")
@click.pass_context
def yard_show(ctx: click.Context, tag: str, on: date) -> None:
    """One module, with where it stands in the yard."""
    holder = context(ctx)

    def work() -> list[str]:
        module = holder.book.modules.get(tag)
        entry = entry_for(holder.book, module.tag, on)
        hold = holder.book.holds.open_for(module.tag)
        run = holder.book.runs.run_of(module.tag)
        return [
            f"{module.tag}  {module.kind}  field {module.field}",
            f"  harvested {module.harvested}  received {module.received}",
            f"  {format_pounds(module.net_pounds)} at {module.moisture_pct}%",
            f"  {entry.days_in_yard} days in the yard, {entry.points} points"
            f"{'  AT RISK' if entry.at_risk else ''}",
            f"  hold {hold.reason if hold else '-'}",
            f"  run  {run or 'not ginned'}",
        ]

    run_command(work)


@yard.command("hold")
@click.argument("tag")
@click.option(
    "--reason",
    type=click.Choice([reason.value for reason in HoldReason]),
    required=True,
    help="why the module is being held",
)
@click.option("--on", type=DATE, required=True, help="the day the hold is placed")
@click.option("--by", default="", help="who placed it")
@click.option("--note", default="", help="anything worth recording")
@click.pass_context
def yard_hold(ctx: click.Context, tag: str, reason: str, on: date, by: str, note: str) -> None:
    """Hold a module so it does not gin."""
    holder = context(ctx)

    def work() -> list[str]:
        with holder.book.writing() as writing:
            hold = place(writing, tag, HoldReason(reason), on, by, note)
        return [f"held {hold.module} for {hold.reason} on {hold.placed}"]

    run_command(work)


@yard.command("lift")
@click.argument("tag")
@click.option("--on", type=DATE, required=True, help="the day the hold is lifted")
@click.option("--by", default="", help="who lifted it")
@click.pass_context
def yard_lift(ctx: click.Context, tag: str, on: date, by: str) -> None:
    """Take the hold off a module."""
    holder = context(ctx)

    def work() -> list[str]:
        with holder.book.writing() as writing:
            hold = lift(writing, tag, on, by)
        return [f"lifted the {hold.reason} hold on {hold.module} after {hold.days_held(on)} days"]

    run_command(work)


@yard.command("standing")
@click.option("--on", type=DATE, required=True, help="the day to work it out at")
@click.pass_context
def yard_standing(ctx: click.Context, on: date) -> None:
    """Everything unginned, worst first."""
    holder = context(ctx)
    run_command(lambda: standing(holder.book, on).render())


@yard.command("queue")
@click.option("--on", type=DATE, required=True, help="the day to work it out at")
@click.option("--no-group", is_flag=True, help="do not keep a producer's modules together")
@click.pass_context
def yard_queue(ctx: click.Context, on: date, no_group: bool) -> None:
    """The order the yard should feed."""
    holder = context(ctx)
    run_command(lambda: ginning_queue(holder.book, on, not no_group).render())


@yard.command("holds")
@click.option("--on", type=DATE, required=True, help="the day to count the days held to")
@click.pass_context
def yard_holds(ctx: click.Context, on: date) -> None:
    """Everything the yard is holding."""
    holder = context(ctx)
    run_command(lambda: holds(holder.book, on).render())
