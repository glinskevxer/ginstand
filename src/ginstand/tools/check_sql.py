"""Values reach sqlite as parameters, never as text in the statement.

There is exactly one safe way to put a value into a query and this package uses
it everywhere: a question mark and a parameter. Anything else is an injection
waiting for a producer whose farm is called O'Neill, which is not a hypothetical
name in cotton country.

Some interpolation is unavoidable, because sqlite will not take a table name as
a parameter and the repository base builds its queries from the table it is for.
So interpolation is allowed from a short list of things that cannot carry a
value, and refused from everything else. The list is here rather than per file,
so adding to it is a decision somebody makes on purpose, and every entry on it
says where it comes from.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

from ginstand.tools.base import Finding, run, source_files

QUERY_METHODS = {"execute", "executemany", "executescript"}

ALLOWED = {
    "self.table",
    "self.key_column",
    "self.order_by",
    "table",
    "where",
    "MIGRATION_TABLE",
    "names",
    "placeholders",
}
"""Interpolations that cannot carry a value, whatever is in them.

The first five are table and column names the code holds itself. The last two
are the importer's, and they are on the list for a reason worth writing down:
``names`` is a join of the columns sqlite reported for the table, and
``placeholders`` is a run of question marks as long as that list. Neither one
can carry a value, because neither one is built from a value: the row's cells go
in as parameters underneath them."""


def _interpolations(node: ast.JoinedStr) -> Iterator[str]:
    for part in node.values:
        if isinstance(part, ast.FormattedValue):
            yield ast.unparse(part.value)


def check_file(path: Path) -> Iterator[Finding]:
    """Every query in one file that builds its statement out of text."""
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = node.func
        if not isinstance(target, ast.Attribute) or target.attr not in QUERY_METHODS:
            continue
        if not node.args:
            continue
        statement = node.args[0]
        if isinstance(statement, ast.JoinedStr):
            for expression in _interpolations(statement):
                if expression not in ALLOWED:
                    yield Finding(
                        path,
                        node.lineno,
                        f"the query interpolates {expression}, which is not an identifier",
                    )
        elif isinstance(statement, ast.BinOp) and isinstance(statement.op, ast.Mod | ast.Add):
            yield Finding(path, node.lineno, "the query is built by joining strings")
        elif (
            isinstance(statement, ast.Call)
            and isinstance(statement.func, ast.Attribute)
            and statement.func.attr == "format"
        ):
            yield Finding(path, node.lineno, "the query is built with format()")


def findings() -> Iterator[Finding]:
    """Every query in the package that does not use parameters."""
    for path in source_files():
        yield from check_file(path)


def main() -> None:
    """Run the check."""
    run("check_sql", findings())


if __name__ == "__main__":
    main()
