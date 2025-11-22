"""Commands for the gin itself: runs, the press, and the run sheet."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import click

from ginstand.cli.common import DATE, NUMBER, context, run_command
from ginstand.ginning.allocate import allocate, plan
from ginstand.ginning.press import press
from ginstand.ginning.restore import highest_allowed
from ginstand.ginning.run import close_run, current_run, feed, open_run
from ginstand.ginning.seed import record_load, seed_pounds
from ginstand.report.run import allocation_sheet, bale_sheet, feed_sheet, run_sheet
from ginstand.units.weight import format_pounds
from ginstand.yard.order import queue


@click.group()
def run() -> None:
    """Gin runs."""


@run.command("open")
@click.argument("ref")
@click.option("--gin-code", required=True, help="the five digit classing office code")
@click.option("--on", type=DATE, required=True, help="the day the run opens")
@click.option("--shift", default="", help="which shift is on")
@click.option("--note", default="", help="anything worth recording")
@click.pass_context
def run_open(ctx: click.Context, ref: str, gin_code: str, on: date, shift: str, note: str) -> None:
    """Open a run. Only one can be open at a time."""
    holder = context(ctx)

    def work() -> list[str]:
        with holder.book.writing() as writing:
            opened = open_run(writing, ref, gin_code, on, shift, note)
        return [f"opened gin run {opened.ref} for crop year {opened.crop_year}"]

    run_command(work)


@run.command("feed")
@click.argument("ref")
@click.argument("modules", nargs=-1, required=True)
@click.option("--on", type=DATE, required=True, help="the day they go on the stands")
@click.pass_context
def run_feed(ctx: click.Context, ref: str, modules: tuple[str, ...], on: date) -> None:
    """Feed modules into a run, in the order given."""
    holder = context(ctx)

    def work() -> list[str]:
        lines = []
        with holder.book.writing() as writing:
            for tag in modules:
                position = feed(writing, ref, tag, on)
                lines.append(f"{position:>3}  {tag.strip().upper()}")
        return lines

    run_command(work)


@run.command("feed-queue")
@click.argument("ref")
@click.option("--on", type=DATE, required=True, help="the day they go on the stands")
@click.option("--limit", type=int, default=0, help="feed at most this many modules")
@click.pass_context
def run_feed_queue(ctx: click.Context, ref: str, on: date, limit: int) -> None:
    """Feed whatever the yard queue says should gin next."""
    holder = context(ctx)

    def work() -> list[str]:
        tags = tuple(module.tag for module in holder.book.modules.unginned())
        wanted = queue(holder.book, tags, on)
        if limit > 0:
            wanted = wanted[:limit]
        if not wanted:
            return ["nothing is free to gin"]
        lines = []
        with holder.book.writing() as writing:
            for tag in wanted:
                position = feed(writing, ref, tag, on)
                lines.append(f"{position:>3}  {tag}")
        return lines

    run_command(work)


@run.command("press")
@click.argument("ref")
@click.option("--on", type=DATE, required=True, help="the day the bale came off")
@click.option("--gross", type=int, required=True, help="gross weight in pounds")
@click.option("--tare", type=int, required=True, help="bagging and ties in pounds")
@click.option("--moisture", type=NUMBER, required=True, help="moisture at the press")
@click.option("--stand", default="", help="which stand it came off")
@click.option("--count", type=int, default=1, show_default=True, help="how many bales")
@click.pass_context
def run_press(
    ctx: click.Context,
    ref: str,
    on: date,
    gross: int,
    tare: int,
    moisture: Decimal,
    stand: str,
    count: int,
) -> None:
    """Take bales off the press."""
    holder = context(ctx)

    def work() -> list[str]:
        if count < 1:
            return ["nothing to press"]
        lines = []
        with holder.book.writing() as writing:
            for _ in range(count):
                bale = press(writing, ref, on, gross, tare, moisture, stand)
                lines.append(f"{bale.tag}  {format_pounds(bale.net_pounds)}")
        return lines

    run_command(work)


@run.command("restore")
@click.option("--pressed", type=int, required=True, help="the bale's weight at the press")
@click.option("--from", "from_moisture", type=NUMBER, required=True, help="moisture now")
@click.pass_context
def run_restore(ctx: click.Context, pressed: int, from_moisture: Decimal) -> None:
    """The wettest a bale of this weight may be taken to."""
    context(ctx)

    def work() -> list[str]:
        reached = highest_allowed(pressed, from_moisture)
        return [f"a {pressed} lb bale at {from_moisture}% may be taken to {reached}%"]

    run_command(work)


@run.command("close")
@click.argument("ref")
@click.option("--on", type=DATE, required=True, help="the day the run closes")
@click.option("--allocate", "do_allocate", is_flag=True, help="allocate the bales as well")
@click.pass_context
def run_close(ctx: click.Context, ref: str, on: date, do_allocate: bool) -> None:
    """Close a run so its turnout is final."""
    holder = context(ctx)

    def work() -> list[str]:
        with holder.book.writing() as writing:
            closed = close_run(writing, ref, on)
            lines = [f"closed gin run {closed.ref} on {closed.closed}"]
            if do_allocate:
                split = allocate(writing, closed.ref, on)
                lines.extend(share.line for share in split.shares)
        return lines

    run_command(work)


@run.command("seed")
@click.argument("ref")
@click.option("--on", type=DATE, required=True, help="the day the load was weighed")
@click.option("--pounds", type=int, required=True, help="net weight of the load")
@click.option("--ticket", default="", help="the seed house ticket number")
@click.option("--buyer", default="", help="who took it")
@click.pass_context
def run_seed(ctx: click.Context, ref: str, on: date, pounds: int, ticket: str, buyer: str) -> None:
    """Book a truckload of cottonseed against a run."""
    holder = context(ctx)

    def work() -> list[str]:
        with holder.book.writing() as writing:
            load = record_load(writing, ref, on, pounds, ticket, buyer)
        total = seed_pounds(holder.book, ref)
        return [
            f"booked {format_pounds(load.net_pounds)} of seed against {load.run}",
            f"{format_pounds(total)} of seed on this run so far",
        ]

    run_command(work)


@run.command("allocate")
@click.argument("ref")
@click.option("--on", type=DATE, required=True, help="the day the allocation is made")
@click.option("--dry-run", is_flag=True, help="work it out without writing it")
@click.pass_context
def run_allocate(ctx: click.Context, ref: str, on: date, dry_run: bool) -> None:
    """Give a closed run's bales to the producers who fed it."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        if dry_run:
            split = plan(holder.book, ref)
            return tuple(share.line for share in split.shares)
        with holder.book.writing() as writing:
            allocate(writing, ref, on)
        return allocation_sheet(holder.book, ref).render()

    run_command(work)


@run.command("sheet")
@click.argument("ref")
@click.option("--feed-only", is_flag=True, help="just the feed sheet")
@click.option("--bales-only", is_flag=True, help="just the bale list")
@click.pass_context
def run_sheet_command(ctx: click.Context, ref: str, feed_only: bool, bales_only: bool) -> None:
    """The run sheet."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        if feed_only:
            return feed_sheet(holder.book, ref).render()
        if bales_only:
            return bale_sheet(holder.book, ref).render()
        return run_sheet(holder.book, ref)

    run_command(work)


@run.command("current")
@click.pass_context
def run_current(ctx: click.Context) -> None:
    """Which run is open, if any."""
    holder = context(ctx)

    def work() -> list[str]:
        open_now = current_run(holder.book)
        if open_now is None:
            return ["no gin run is open"]
        fed = len(holder.book.runs.modules_in(open_now.ref))
        pressed = holder.book.bales.count_for_run(open_now.ref)
        return [f"{open_now.ref} opened {open_now.opened}, {fed} modules, {pressed} bales"]

    run_command(work)
