"""Commands for the farm and field registers."""

from __future__ import annotations

from decimal import Decimal

import click

from ginstand.cli.common import NUMBER, context, run_command
from ginstand.model.farm import Farm, Field
from ginstand.report.table import Align, Column, Table


@click.group()
def farm() -> None:
    """The farm register."""


@farm.command("add")
@click.argument("ref")
@click.argument("producer")
@click.argument("name")
@click.option("--fsa", "fsa_number", default="", help="the farm agency number")
@click.option("--county", default="", help="the county the farm is in")
@click.pass_context
def farm_add(
    ctx: click.Context, ref: str, producer: str, name: str, fsa_number: str, county: str
) -> None:
    """Put a farm in the book."""
    holder = context(ctx)

    def work() -> list[str]:
        record = Farm(ref=ref, producer=producer, name=name, fsa_number=fsa_number, county=county)
        holder.book.producers.get(record.producer)
        with holder.book.writing() as writing:
            writing.farms.add(record)
        return [f"added farm {record.ref} {record.name} for {record.producer}"]

    run_command(work)


@farm.command("list")
@click.option("--producer", default="", help="only this producer's farms")
@click.pass_context
def farm_list(ctx: click.Context, producer: str) -> None:
    """Every farm in the book, or one producer's."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        farms = (
            holder.book.farms.for_producer(producer) if producer else holder.book.farms.list_all()
        )
        rows = tuple(
            (
                record.ref,
                record.producer,
                record.name,
                record.county,
                str(len(holder.book.fields.for_farm(record.ref))),
            )
            for record in farms
        )
        return Table(
            title="Farms",
            columns=(
                Column("ref"),
                Column("producer"),
                Column("name"),
                Column("county"),
                Column("fields", Align.RIGHT),
            ),
            rows=rows,
            empty_note="no farms yet",
        ).render()

    run_command(work)


@click.group()
def field() -> None:
    """The field register."""


@field.command("add")
@click.argument("ref")
@click.argument("farm_ref")
@click.argument("name")
@click.option("--acres", type=NUMBER, required=True, help="acres in the field")
@click.option("--lease", required=True, help="the lease this field is farmed under")
@click.option("--variety", default="", help="the variety planted")
@click.option("--irrigated", is_flag=True, help="the field is irrigated")
@click.pass_context
def field_add(
    ctx: click.Context,
    ref: str,
    farm_ref: str,
    name: str,
    acres: Decimal,
    lease: str,
    variety: str,
    irrigated: bool,
) -> None:
    """Put a field in the book."""
    holder = context(ctx)

    def work() -> list[str]:
        record = Field(
            ref=ref,
            farm=farm_ref,
            name=name,
            acres=acres,
            lease=lease,
            variety=variety,
            irrigated=irrigated,
        )
        holder.book.farms.get(record.farm)
        holder.book.leases.get(record.lease)
        with holder.book.writing() as writing:
            writing.fields.add(record)
        return [f"added field {record.ref} {record.name}, {record.acres} acres"]

    run_command(work)


@field.command("list")
@click.option("--farm", "farm_ref", default="", help="only this farm's fields")
@click.pass_context
def field_list(ctx: click.Context, farm_ref: str) -> None:
    """Every field in the book, or one farm's."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        fields = (
            holder.book.fields.for_farm(farm_ref) if farm_ref else holder.book.fields.list_all()
        )
        rows = tuple(
            (
                record.ref,
                record.farm,
                record.name,
                str(record.acres),
                record.lease,
                record.variety,
                "yes" if record.irrigated else "",
            )
            for record in fields
        )
        total = sum((record.acres for record in fields), Decimal("0"))
        return Table(
            title="Fields",
            columns=(
                Column("ref"),
                Column("farm"),
                Column("name"),
                Column("acres", Align.RIGHT),
                Column("lease"),
                Column("variety"),
                Column("irrigated"),
            ),
            rows=rows,
            footers=(("", "", "", str(total), "", "", ""),),
            empty_note="no fields yet",
        ).render()

    run_command(work)


@farm.command("edit")
@click.argument("ref")
@click.option("--name", default=None, help="a new name")
@click.option("--fsa", "fsa_number", default=None, help="a new farm agency number")
@click.option("--county", default=None, help="a new county")
@click.pass_context
def farm_edit(
    ctx: click.Context,
    ref: str,
    name: str | None,
    fsa_number: str | None,
    county: str | None,
) -> None:
    """Change what the book says about a farm. Only what is given changes."""
    holder = context(ctx)

    def work() -> list[str]:
        standing = holder.book.farms.get(ref)
        changed = Farm(
            ref=standing.ref,
            producer=standing.producer,
            name=standing.name if name is None else name,
            fsa_number=standing.fsa_number if fsa_number is None else fsa_number,
            county=standing.county if county is None else county,
        )
        if changed == standing:
            return [f"{standing.ref} is unchanged"]
        with holder.book.writing() as writing:
            writing.farms.update(changed)
        return [f"changed farm {changed.ref} {changed.name}"]

    run_command(work)


@field.command("edit")
@click.argument("ref")
@click.option("--name", default=None, help="a new name")
@click.option("--acres", type=NUMBER, default=None, help="a corrected acreage")
@click.option("--lease", default=None, help="the lease it is really farmed under")
@click.option("--variety", default=None, help="what was actually planted")
@click.option("--irrigated/--dryland", default=None, help="whether it is irrigated")
@click.pass_context
def field_edit(
    ctx: click.Context,
    ref: str,
    name: str | None,
    acres: Decimal | None,
    lease: str | None,
    variety: str | None,
    irrigated: bool | None,
) -> None:
    """Change what the book says about a field. Only what is given changes.

    The lease can be moved, and it is worth knowing that moving it does not move
    a settlement that has already been posted. It changes who the next one is
    split with, which is nearly always what somebody correcting a lease means.
    """
    holder = context(ctx)

    def work() -> list[str]:
        standing = holder.book.fields.get(ref)
        if lease is not None:
            holder.book.leases.get(lease)
        changed = Field(
            ref=standing.ref,
            farm=standing.farm,
            name=standing.name if name is None else name,
            acres=standing.acres if acres is None else acres,
            lease=standing.lease if lease is None else lease,
            variety=standing.variety if variety is None else variety,
            irrigated=standing.irrigated if irrigated is None else irrigated,
        )
        if changed == standing:
            return [f"{standing.ref} is unchanged"]
        with holder.book.writing() as writing:
            writing.fields.update(changed)
        return [
            f"changed field {changed.ref} {changed.name}, "
            f"{changed.acres} acres under {changed.lease}"
        ]

    run_command(work)
