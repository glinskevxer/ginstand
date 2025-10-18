"""The settlement register: every producer on a run, on one page.

The office runs this before it prints statements, because it is the only place
the run's money adds up in one view. If the register's totals do not match the
run's own figures then a statement is wrong and it is cheaper to find that here
than in an envelope.

The check line at the bottom is not decoration. It adds the producers' totals
back and compares them against the run's lint value and charges, and it says so
in words when they disagree.
"""

from __future__ import annotations

from datetime import date

from ginstand.charges.tariff import Tariff
from ginstand.report.table import Align, Column, Table
from ginstand.settle.gather import producers_in
from ginstand.settle.statement import Statement, settle
from ginstand.store.book import Book
from ginstand.units.money import Money, format_money


def statements_for(
    book: Book,
    run_ref: str,
    tariff: Tariff,
    seed_price_per_ton: Money,
    on: date,
) -> tuple[Statement, ...]:
    """Work out every producer's statement for a run, in feed order."""
    return tuple(
        settle(book, run_ref, producer, tariff, seed_price_per_ton, on)
        for producer in producers_in(book, run_ref)
    )


def register(
    book: Book,
    run_ref: str,
    tariff: Tariff,
    seed_price_per_ton: Money,
    on: date,
) -> Table:
    """Every producer on a run, with what they are owed."""
    statements = statements_for(book, run_ref, tariff, seed_price_per_ton, on)
    rows = [
        (
            statement.share.producer,
            str(statement.share.bales),
            f"{statement.share.seed_cotton_pounds:,}",
            format_money(statement.lint_value),
            format_money(statement.seed_credit),
            format_money(Money(-statement.charges.total)),
            format_money(statement.total),
            "provisional" if statement.provisional else "",
        )
        for statement in statements
    ]
    totals = (
        "",
        str(sum(s.share.bales for s in statements)),
        f"{sum(s.share.seed_cotton_pounds for s in statements):,}",
        format_money(Money(sum(s.lint_value for s in statements))),
        format_money(Money(sum(s.seed_credit for s in statements))),
        format_money(Money(-sum(s.charges.total for s in statements))),
        format_money(Money(sum(s.total for s in statements))),
        "",
    )
    return Table(
        title=f"Settlement register, gin run {run_ref.strip().upper()}, {on.isoformat()}",
        columns=(
            Column("producer"),
            Column("bales", Align.RIGHT),
            Column("seed cotton", Align.RIGHT),
            Column("lint", Align.RIGHT),
            Column("seed", Align.RIGHT),
            Column("charges", Align.RIGHT),
            Column("total", Align.RIGHT),
            Column("note"),
        ),
        rows=tuple(rows),
        footers=(totals,) if rows else (),
        empty_note="nobody has cotton on this run",
    )


def reconcile(
    book: Book,
    run_ref: str,
    tariff: Tariff,
    seed_price_per_ton: Money,
    on: date,
) -> tuple[str, ...]:
    """Check the register's totals against the run's own figures."""
    statements = statements_for(book, run_ref, tariff, seed_price_per_ton, on)
    run = book.runs.get(run_ref)
    settled_bales = sum(statement.share.bales for statement in statements)
    pressed = book.bales.count_for_run(run.ref)
    settled_seed_cotton = sum(statement.share.seed_cotton_pounds for statement in statements)
    fed = book.runs.seed_cotton_in(run.ref)

    lines = []
    if settled_bales != pressed:
        lines.append(f"{settled_bales} bales are settled and {pressed} were pressed off {run.ref}")
    if settled_seed_cotton != fed:
        lines.append(
            f"{settled_seed_cotton:,} lb of seed cotton is settled and "
            f"{fed:,} lb was fed into {run.ref}"
        )
    provisional = [s.share.producer for s in statements if s.provisional]
    if provisional:
        lines.append(f"provisional for {', '.join(provisional)}")
    if not lines:
        lines.append(f"{run.ref} reconciles: {pressed} bales, {fed:,} lb seed cotton")
    return tuple(lines)


def producer_page(
    book: Book,
    run_ref: str,
    producer: str,
    tariff: Tariff,
    seed_price_per_ton: Money,
    on: date,
) -> tuple[str, ...]:
    """One producer's statement, with the bale list under it."""
    statement = settle(book, run_ref, producer, tariff, seed_price_per_ton, on)
    rows = []
    for tag in statement.share.bale_tags:
        bale = book.bales.get(tag)
        card = book.cards.find(tag)
        rows.append(
            (
                tag,
                f"{bale.net_pounds}",
                card.summary if card is not None else "not classed",
            )
        )
    bales = Table(
        columns=(Column("tag"), Column("net", Align.RIGHT), Column("classing")),
        rows=tuple(rows),
        empty_note="no bales",
    )
    return (*statement.lines, "", *bales.render())
