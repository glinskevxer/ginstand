"""Commands for classing cards."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import click

from ginstand.classing.estimate import Reading
from ginstand.classing.filing import file_reading, outstanding
from ginstand.classing.ingest import read
from ginstand.classing.recheck import outstanding as open_rechecks
from ginstand.classing.recheck import request, settle, to_chase
from ginstand.classing.standing import standing_of
from ginstand.cli.common import DATE, NUMBER, context, run_command
from ginstand.model.recheck import RecheckOutcome, RecheckReason
from ginstand.report.table import Align, Column, Table


@click.group()
def card() -> None:
    """Classing cards."""


@card.command("file")
@click.argument("path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--recheck", is_flag=True, help="this file replaces cards already filed")
@click.option("--dry-run", is_flag=True, help="read the file without filing it")
@click.pass_context
def card_file(ctx: click.Context, path: Path, recheck: bool, dry_run: bool) -> None:
    """Read a classing file and file it against the bales."""
    holder = context(ctx)

    def work() -> list[str]:
        reading = read(path.read_text())
        lines = [reading.summary]
        lines.extend(problem.line for problem in reading.problems)
        if dry_run:
            return lines
        with holder.book.writing() as writing:
            filing = file_reading(writing, reading, recheck)
        lines.append(filing.summary)
        lines.extend(f"{item.tag}: {item.reason}" for item in filing.rejected)
        return lines

    run_command(work)


@card.command("show")
@click.argument("tag")
@click.pass_context
def card_show(ctx: click.Context, tag: str) -> None:
    """One bale's card, and where it stands against the schedule."""
    holder = context(ctx)

    def work() -> list[str]:
        record = holder.book.cards.get(tag)
        bale = holder.book.bales.get(record.tag)
        standing = standing_of(record)
        return [
            f"{record.tag}  classed {record.classed}  office {record.office or '-'}",
            f"  colour   {record.color.code} {record.color.name}",
            f"  leaf     {record.leaf}",
            f"  staple   {record.staple}",
            f"  mic      {record.micronaire}",
            f"  strength {record.strength}",
            f"  unif     {record.uniformity}",
            f"  trash    {record.trash_pct}%",
            f"  notes    {record.codes or '-'}",
            f"  bale     {bale.net_pounds} lb off run {bale.run}",
            f"  {standing.line}",
        ]

    run_command(work)


@card.command("list")
@click.option("--run", "run_ref", default="", help="only bales off this run")
@click.pass_context
def card_list(ctx: click.Context, run_ref: str) -> None:
    """Every card filed, or one run's."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        cards = holder.book.cards.for_run(run_ref) if run_ref else holder.book.cards.list_all()
        rows = tuple(
            (
                record.tag,
                str(record.color.code),
                str(record.leaf),
                str(record.staple),
                str(record.micronaire),
                str(record.strength),
                str(record.uniformity),
                record.codes,
            )
            for record in cards
        )
        return Table(
            title="Classing cards",
            columns=(
                Column("tag"),
                Column("colour", Align.RIGHT),
                Column("leaf", Align.RIGHT),
                Column("staple", Align.RIGHT),
                Column("mic", Align.RIGHT),
                Column("str", Align.RIGHT),
                Column("unif", Align.RIGHT),
                Column("notes"),
            ),
            rows=rows,
            empty_note="nothing has been classed",
        ).render()

    run_command(work)


@card.command("outstanding")
@click.pass_context
def card_outstanding(ctx: click.Context) -> None:
    """Every bale still waiting on a card."""
    holder = context(ctx)

    def work() -> list[str]:
        waiting = outstanding(holder.book)
        if not waiting:
            return ["every bale has been classed"]
        return [f"{len(waiting)} bales waiting", *waiting]

    run_command(work)


@card.command("estimate")
@click.option("--rd", type=NUMBER, required=True, help="reflectance off the colorimeter")
@click.option("--plus-b", type=NUMBER, required=True, help="yellowness off the colorimeter")
@click.pass_context
def card_estimate(ctx: click.Context, rd: Decimal, plus_b: Decimal) -> None:
    """What the gin's own instrument would call this sample."""
    context(ctx)

    def work() -> list[str]:
        reading = Reading(rd=rd, plus_b=plus_b)
        grade = reading.grade
        return [
            f"Rd {reading.rd}  +b {reading.plus_b}",
            f"  {grade.code}  {grade.name}",
            "  this is the gin's estimate, the card is what counts",
        ]

    run_command(work)


@click.group()
def recheck() -> None:
    """Recheck requests against a classing card."""


@recheck.command("ask")
@click.argument("tag")
@click.option(
    "--reason",
    type=click.Choice([reason.value for reason in RecheckReason]),
    required=True,
    help="what the gin thinks is wrong",
)
@click.option("--on", type=DATE, required=True, help="the day the request is sent")
@click.option("--by", default="", help="who asked")
@click.option("--note", default="", help="anything worth recording")
@click.pass_context
def recheck_ask(ctx: click.Context, tag: str, reason: str, on: date, by: str, note: str) -> None:
    """Ask the office to read a sample again."""
    holder = context(ctx)

    def work() -> list[str]:
        with holder.book.writing() as writing:
            sent = request(writing, tag, RecheckReason(reason), on, by, note)
        return [f"recheck {sent.recheck_id} sent on {sent.tag} for {sent.reason}"]

    run_command(work)


@recheck.command("settle")
@click.argument("tag")
@click.option(
    "--outcome",
    type=click.Choice(
        [outcome.value for outcome in RecheckOutcome if outcome is not RecheckOutcome.OPEN]
    ),
    required=True,
    help="what the office said",
)
@click.option("--on", type=DATE, required=True, help="the day the answer came back")
@click.option("--note", default="", help="anything worth recording")
@click.pass_context
def recheck_settle(ctx: click.Context, tag: str, outcome: str, on: date, note: str) -> None:
    """Answer an open request by hand."""
    holder = context(ctx)

    def work() -> list[str]:
        with holder.book.writing() as writing:
            answered = settle(writing, tag, on, RecheckOutcome(outcome), note)
        return [
            f"recheck on {answered.tag} came back {answered.outcome} "
            f"after {answered.days_out(on)} days"
        ]

    run_command(work)


@recheck.command("list")
@click.option("--on", type=DATE, required=True, help="the day to count the days out to")
@click.option("--chase", is_flag=True, help="only the ones out too long")
@click.pass_context
def recheck_list(ctx: click.Context, on: date, chase: bool) -> None:
    """Every request the office still has."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        found = tuple(to_chase(holder.book, on)) if chase else open_rechecks(holder.book)
        rows = tuple(
            (
                str(item.recheck_id),
                item.tag,
                str(item.reason),
                item.requested.isoformat(),
                str(item.days_out(on)),
                item.requested_by,
            )
            for item in found
        )
        return Table(
            title="Rechecks out" + (" too long" if chase else ""),
            columns=(
                Column("id", Align.RIGHT),
                Column("bale"),
                Column("reason"),
                Column("sent"),
                Column("days", Align.RIGHT),
                Column("by"),
            ),
            rows=rows,
            empty_note="nothing is out",
        ).render()

    run_command(work)


@recheck.command("history")
@click.argument("tag")
@click.pass_context
def recheck_history(ctx: click.Context, tag: str) -> None:
    """Every request ever made against one bale."""
    holder = context(ctx)

    def work() -> tuple[str, ...]:
        rows = tuple(
            (
                str(item.recheck_id),
                str(item.reason),
                item.requested.isoformat(),
                item.settled.isoformat() if item.settled else "",
                str(item.outcome),
                item.note,
            )
            for item in holder.book.rechecks.history_for(tag)
        )
        return Table(
            title=f"Rechecks on bale {tag.strip()}",
            columns=(
                Column("id", Align.RIGHT),
                Column("reason"),
                Column("sent"),
                Column("answered"),
                Column("outcome"),
                Column("what moved"),
            ),
            rows=rows,
            empty_note="this bale has never been rechecked",
        ).render()

    run_command(work)
