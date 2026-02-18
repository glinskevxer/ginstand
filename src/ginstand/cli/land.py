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
