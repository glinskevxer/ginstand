"""Commands for warehouses, receipts and storage."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import click

from ginstand.charges.published import storage_for
from ginstand.cli.common import DATE, context, run_command
from ginstand.model.warehouse import Warehouse
from ginstand.report.position import position_table
from ginstand.report.table import Align, Column, Table
from ginstand.units.money import Money, format_money
from ginstand.warehouse.ewr import build
from ginstand.warehouse.receipts import issue, release, transfer
from ginstand.warehouse.storage import bill_holder


@click.group()
def warehouse() -> None:
    """Warehouses and the receipts they issue."""


@warehouse.command("add")
@click.argument("ref")
@click.argument("name")
@click.option("--code", default="", help="the licensed warehouse code")
@click.option("--location", default="", help="where it is")
@click.pass_context
def warehouse_add(ctx: click.Context, ref: str, name: str, code: str, location: str) -> None:
    """Put a warehouse in the book."""
    holder = context(ctx)

    def work() -> list[str]:
        house = Warehouse(ref=ref, name=name, code=code, location=location)
        with holder.book.writing() as writing:
            writing.warehouses.add(house)
        licensed = "licensed" if house.licensed else "not licensed"
        return [f"added warehouse {house.ref} {house.name} ({licensed})"]

    run_command(work)


@warehouse.command("list")
@click.pass_context
def warehouse_list(ctx: click.Context) -> None:
    """Every warehouse, with what it is holding."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        rows = tuple(
            (
                house.ref,
                house.name,
                house.code,
                house.location,
                str(len(holder.book.receipts.in_warehouse(house.ref))),
            )
            for house in holder.book.warehouses.list_all()
        )
        return Table(
            title="Warehouses",
            columns=(
                Column("ref"),
                Column("name"),
                Column("code"),
                Column("location"),
                Column("in store", Align.RIGHT),
            ),
            rows=rows,
            empty_note="no warehouses yet",
        ).render()

    run_command(work)


@click.group()
def receipt() -> None:
    """Warehouse receipts."""


@receipt.command("issue")
@click.argument("tags", nargs=-1, required=True)
@click.option("--warehouse", "house", required=True, help="which warehouse")
@click.option("--on", type=DATE, required=True, help="the day it goes into store")
@click.option("--holder", "to_holder", default="", help="who holds it, if not the owner")
@click.pass_context
def receipt_issue(
    ctx: click.Context, tags: tuple[str, ...], house: str, on: date, to_holder: str
) -> None:
    """Put bales into store and issue their receipts."""
    holder = context(ctx)

    def work() -> list[str]:
        lines = []
        with holder.book.writing() as writing:
            for tag in tags:
                record = issue(writing, tag, house, on, to_holder)
                lines.append(f"{record.number}  {record.tag}  {record.holder}")
        return lines

    run_command(work)


@receipt.command("release")
@click.argument("number")
@click.option("--on", type=DATE, required=True, help="the day it comes out")
@click.pass_context
def receipt_release(ctx: click.Context, number: str, on: date) -> None:
    """Take a bale back out of store."""
    holder = context(ctx)

    def work() -> list[str]:
        with holder.book.writing() as writing:
            record = release(writing, number, on)
        return [
            f"released {record.number} on {record.released} after {record.days_stored(on)} days"
        ]

    run_command(work)


@receipt.command("transfer")
@click.argument("number")
@click.argument("to_holder")
@click.pass_context
def receipt_transfer(ctx: click.Context, number: str, to_holder: str) -> None:
    """Move a receipt into somebody else's hands."""
    holder = context(ctx)

    def work() -> list[str]:
        with holder.book.writing() as writing:
            record = transfer(writing, number, to_holder)
        return [f"{record.number} is now held by {record.holder}"]

    run_command(work)


@receipt.command("list")
@click.option("--holder", "who", default="", help="only this holder's receipts")
@click.option("--warehouse", "house", default="", help="only this warehouse")
@click.option("--all", "everything", is_flag=True, help="released receipts as well")
@click.pass_context
def receipt_list(ctx: click.Context, who: str, house: str, everything: bool) -> None:
    """Receipts, outstanding by default."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        if who:
            found = (
                holder.book.receipts.for_holder(who)
                if everything
                else holder.book.receipts.outstanding_for(who)
            )
        elif house:
            found = holder.book.receipts.in_warehouse(house)
        else:
            found = (
                holder.book.receipts.list_all()
                if everything
                else holder.book.receipts.outstanding()
            )
        rows = tuple(
            (
                record.number,
                record.tag,
                record.warehouse,
                record.holder,
                record.issued.isoformat(),
                record.released.isoformat() if record.released else "",
            )
            for record in found
        )
        return Table(
            title="Warehouse receipts",
            columns=(
                Column("number"),
                Column("bale"),
                Column("warehouse"),
                Column("holder"),
                Column("issued"),
                Column("released"),
            ),
            rows=rows,
            empty_note="nothing is in store",
        ).render()

    run_command(work)


@receipt.command("storage")
@click.argument("who")
@click.option("--on", type=DATE, required=True, help="the day to bill up to")
@click.option("--crop-year", type=int, required=True, help="which contract applies")
@click.pass_context
def receipt_storage(ctx: click.Context, who: str, on: date, crop_year: int) -> None:
    """What somebody owes the warehouse."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        contract = storage_for(crop_year)
        bills = bill_holder(holder.book, contract, who, on)
        rows = tuple(
            (
                item.receipt,
                item.tag,
                str(item.days_stored),
                str(item.chargeable_days),
                format_money(item.total),
            )
            for item in bills
        )
        total = Money(sum(item.total for item in bills))
        return Table(
            title=f"Storage owed by {who.strip().upper()} at {on.isoformat()}",
            columns=(
                Column("receipt"),
                Column("bale"),
                Column("days", Align.RIGHT),
                Column("charged", Align.RIGHT),
                Column("amount", Align.RIGHT),
            ),
            rows=rows,
            footers=(("", "", "", "", format_money(total)),),
            empty_note="nothing in store",
        ).render()

    run_command(work)


@receipt.command("export")
@click.argument("house")
@click.option("--on", type=DATE, required=True, help="the day the file is made up")
@click.option(
    "--out",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="write the file here instead of printing it",
)
@click.pass_context
def receipt_export(ctx: click.Context, house: str, on: date, out: Path | None) -> None:
    """Make up the receipt file for a warehouse."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        lines = build(holder.book, house, on)
        if out is None:
            return lines
        out.write_text("\n".join(lines) + "\n")
        return (f"wrote {len(lines) - 2} records to {out}",)

    run_command(work)


@warehouse.command("position")
@click.option("--on", type=DATE, required=True, help="the day to price it at")
@click.pass_context
def warehouse_position(ctx: click.Context, on: date) -> None:
    """What is in store, whose it is, and what it is costing to keep."""
    holder = context(ctx)
    run_command(lambda: position_table(holder.book, on).render())


@warehouse.command("edit")
@click.argument("ref")
@click.option("--name", default=None, help="a new name")
@click.option("--code", default=None, help="a new licensed warehouse code")
@click.option("--location", default=None, help="a new location")
@click.pass_context
def warehouse_edit(
    ctx: click.Context,
    ref: str,
    name: str | None,
    code: str | None,
    location: str | None,
) -> None:
    """Change what the book says about a warehouse. Only what is given changes."""
    holder = context(ctx)

    def work() -> list[str]:
        standing = holder.book.warehouses.get(ref)
        changed = Warehouse(
            ref=standing.ref,
            name=standing.name if name is None else name,
            code=standing.code if code is None else code,
            location=standing.location if location is None else location,
        )
        if changed == standing:
            return [f"{standing.ref} is unchanged"]
        with holder.book.writing() as writing:
            writing.warehouses.update(changed)
        licensed = "licensed" if changed.licensed else "not licensed"
        return [f"changed warehouse {changed.ref} {changed.name} ({licensed})"]

    run_command(work)
