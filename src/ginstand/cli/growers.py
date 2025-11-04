"""Commands for the producer and lease registers."""

from __future__ import annotations

from decimal import Decimal

import click

from ginstand.cli.common import NUMBER, context, run_command
from ginstand.model.producer import Lease, LeaseKind, Producer
from ginstand.report.table import Column, Table


@click.group()
def producer() -> None:
    """The producer register."""


@producer.command("add")
@click.argument("ref")
@click.argument("name")
@click.option("--address", default="", help="postal address")
@click.option("--phone", default="", help="telephone number")
@click.option("--ccc", "ccc_number", default="", help="loan farm number, if enrolled")
@click.pass_context
def producer_add(
    ctx: click.Context, ref: str, name: str, address: str, phone: str, ccc_number: str
) -> None:
    """Put a producer in the book."""
    holder = context(ctx)

    def work() -> list[str]:
        record = Producer(ref=ref, name=name, address=address, phone=phone, ccc_number=ccc_number)
        with holder.book.writing() as writing:
            writing.producers.add(record)
        return [f"added producer {record.ref} {record.name}"]

    run_command(work)


@producer.command("list")
@click.pass_context
def producer_list(ctx: click.Context) -> None:
    """Every producer in the book."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        rows = tuple(
            (record.ref, record.name, record.phone, "yes" if record.enrolled_for_loan else "")
            for record in holder.book.producers.list_all()
        )
        return Table(
            title="Producers",
            columns=(Column("ref"), Column("name"), Column("phone"), Column("loan")),
            rows=rows,
            empty_note="no producers yet",
        ).render()

    run_command(work)


@producer.command("show")
@click.argument("ref")
@click.pass_context
def producer_show(ctx: click.Context, ref: str) -> None:
    """One producer, with their farms and leases."""
    holder = context(ctx)

    def work() -> list[str]:
        record = holder.book.producers.get(ref)
        lines = [
            f"{record.ref}  {record.name}",
            f"  address {record.address or '-'}",
            f"  phone   {record.phone or '-'}",
            f"  loan    {record.ccc_number or 'not enrolled'}",
        ]
        farms = holder.book.farms.for_producer(record.ref)
        lines.append(f"  farms   {', '.join(farm.ref for farm in farms) or '-'}")
        leases = holder.book.leases.for_tenant(record.ref)
        lines.append(f"  leases  {', '.join(lease.ref for lease in leases) or '-'}")
        return lines

    run_command(work)


@click.group()
def lease() -> None:
    """The lease register."""


@lease.command("add")
@click.argument("ref")
@click.argument("tenant")
@click.option(
    "--kind",
    type=click.Choice([kind.value for kind in LeaseKind]),
    required=True,
    help="how the crop is divided",
)
@click.option("--landlord", default="", help="the landlord's producer reference")
@click.option("--share", type=NUMBER, default=Decimal("0"), help="the landlord's share")
@click.pass_context
def lease_add(
    ctx: click.Context, ref: str, tenant: str, kind: str, landlord: str, share: Decimal
) -> None:
    """Put a lease in the book."""
    holder = context(ctx)

    def work() -> list[str]:
        record = Lease(
            ref=ref,
            tenant=tenant,
            kind=LeaseKind(kind),
            landlord=landlord,
            landlord_share=share,
        )
        with holder.book.writing() as writing:
            writing.leases.add(record)
        return [f"added lease {record.ref} for {record.tenant} ({record.kind})"]

    run_command(work)


@lease.command("list")
@click.pass_context
def lease_list(ctx: click.Context) -> None:
    """Every lease in the book."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        rows = tuple(
            (
                record.ref,
                record.tenant,
                str(record.kind),
                record.landlord,
                str(record.landlord_share),
            )
            for record in holder.book.leases.list_all()
        )
        return Table(
            title="Leases",
            columns=(
                Column("ref"),
                Column("tenant"),
                Column("kind"),
                Column("landlord"),
                Column("share"),
            ),
            rows=rows,
            empty_note="no leases yet",
        ).render()

    run_command(work)
