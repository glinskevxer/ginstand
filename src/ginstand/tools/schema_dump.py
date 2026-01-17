"""Write the book's schema out as a document, and check it is still current.

The schema is built by applying migrations, which means the only way to see what
a book looks like is to make one. That is fine for code and useless for a person
trying to answer a question about a column at four in the afternoon.

So it is dumped to a file that lives in the repository, and CI checks the file
still matches. Nobody has to remember to regenerate it, because forgetting fails
the build.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from ginstand.store.migrations import MIGRATIONS, apply_pending, latest_version
from ginstand.store.sqlite import opened
from ginstand.tools.base import repo_root

DOCUMENT = "docs/schema.md"


def dump() -> str:
    """The schema of a freshly made book, as a document."""
    with opened(":memory:") as connection:
        apply_pending(connection, date(2025, 8, 1))
        rows = connection.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master"
            " WHERE sql IS NOT NULL ORDER BY tbl_name, type DESC, name"
        ).fetchall()

    lines = [
        "# The book",
        "",
        f"Schema version {latest_version()}, built by {len(MIGRATIONS)} migrations.",
        "",
        "This file is generated. Run `python -m ginstand.tools.schema_dump` after",
        "adding a migration, and CI will tell you if you forgot.",
        "",
        "## Migrations",
        "",
    ]
    for migration in MIGRATIONS:
        lines.append(f"{migration.version}. {migration.name}")
    lines.extend(["", "## Tables", ""])

    current = ""
    for row in rows:
        table = str(row["tbl_name"])
        if table != current:
            current = table
            lines.extend([f"### {table}", ""])
        statement = " ".join(str(row["sql"]).split())
        if str(row["type"]) == "table":
            lines.extend(["```sql", _wrap(statement), "```", ""])
        else:
            lines.extend([f"- `{statement}`", ""])
    return "\n".join(lines).rstrip() + "\n"


def _wrap(statement: str) -> str:
    """Put one column definition on each line.

    Splitting on every comma breaks a compound primary key across two lines, so
    the split only happens at the top level of the brackets.
    """
    head, _, body = statement.partition("(")
    if not body:
        return statement
    inner = ",\n    ".join(_top_level(body.rstrip().rstrip(")")))
    return f"{head.strip()} (\n    {inner}\n)"


def _top_level(body: str) -> list[str]:
    """The comma separated parts of a bracket body, ignoring nested brackets."""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for character in body:
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
        if character == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(character)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def main() -> None:
    """Write the document, or check the one on disk still matches."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="do not write, compare")
    args = parser.parse_args()

    path = repo_root() / DOCUMENT
    wanted = dump()
    if not args.check:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(wanted)
        print(f"schema_dump: wrote {DOCUMENT}")
        return
    if not path.is_file():
        print(f"schema_dump: {DOCUMENT} is not there, run this without --check")
        sys.exit(1)
    if path.read_text() != wanted:
        print(f"schema_dump: {DOCUMENT} is out of date, run this without --check")
        sys.exit(1)
    print("schema_dump: clean")


if __name__ == "__main__":
    main()
