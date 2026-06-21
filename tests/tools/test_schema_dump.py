"""The schema document, and that the one on disk is still current."""

from __future__ import annotations

import pytest

from ginstand.store.migrations import MIGRATIONS, latest_version
from ginstand.tools.base import repo_root
from ginstand.tools.schema_dump import DOCUMENT, dump, main


def test_the_document_on_disk_is_current() -> None:
    assert (repo_root() / DOCUMENT).read_text() == dump()


def test_the_schema_check_passes_as_it_stands(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.argv", ["schema_dump", "--check"])
    main()
    assert "schema_dump: clean" in capsys.readouterr().out


def test_the_document_names_the_version_and_every_migration() -> None:
    text = dump()
    assert f"Schema version {latest_version()}" in text
    for migration in MIGRATIONS:
        assert migration.name in text


def test_every_table_gets_a_heading_and_its_sql() -> None:
    text = dump()
    for table in ("producer", "module", "bale", "classing", "receipt"):
        assert f"### {table}" in text
    assert "```sql" in text


def test_a_column_goes_on_a_line_of_its_own() -> None:
    text = dump()
    assert "    gross_pounds INTEGER NOT NULL," in text


def test_a_compound_key_stays_on_one_line() -> None:
    assert "PRIMARY KEY (producer, crop_year)" in dump()
    assert "PRIMARY KEY (run, module)" in dump()


def test_the_indexes_are_listed_under_their_table() -> None:
    text = dump()
    assert "CREATE INDEX bale_by_run ON bale(run)" in text
    assert "CREATE UNIQUE INDEX yard_hold_one_active" in text


def test_the_document_says_it_is_generated() -> None:
    assert "This file is generated" in dump()
