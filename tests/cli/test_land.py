"""The farm and field commands."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from click.testing import Result


@pytest.fixture
def growers(gin: Callable[..., Result]) -> Callable[..., Result]:
    gin("producer", "add", "P-12", "Aldys Brothers")
    gin("producer", "add", "P-40", "Merrick Land Co")
    gin("lease", "add", "L-1", "P-12", "--kind", "owner")
    return gin


def test_a_farm_can_be_added_and_listed(growers: Callable[..., Result]) -> None:
    assert growers("farm", "add", "f-3", "p-12", "Home Place").exit_code == 0
    output = growers("farm", "list").output
    assert "F-3" in output
    assert "Home Place" in output


def test_a_farm_for_a_producer_who_is_not_there_is_refused(
    growers: Callable[..., Result],
) -> None:
    result = growers("farm", "add", "F-9", "P-99", "Nowhere")
    assert result.exit_code != 0
    assert "no producer with reference P-99" in result.output


def test_farms_can_be_listed_for_one_producer(growers: Callable[..., Result]) -> None:
    growers("farm", "add", "F-3", "P-12", "Home Place")
    growers("farm", "add", "F-7", "P-40", "River Place")
    output = growers("farm", "list", "--producer", "P-12").output
    assert "F-3" in output
    assert "F-7" not in output


def test_an_empty_farm_register_says_so(growers: Callable[..., Result]) -> None:
    assert "no farms yet" in growers("farm", "list").output


def test_a_field_can_be_added_with_its_acres(growers: Callable[..., Result]) -> None:
    growers("farm", "add", "F-3", "P-12", "Home Place")
    result = growers("field", "add", "fl-9", "f-3", "North 80", "--acres", "78.4", "--lease", "l-1")
    assert result.exit_code == 0
    assert "78.40 acres" in result.output


def test_a_field_on_a_farm_that_is_not_there_is_refused(
    growers: Callable[..., Result],
) -> None:
    result = growers(
        "field", "add", "FL-9", "F-99", "North 80", "--acres", "78.4", "--lease", "L-1"
    )
    assert result.exit_code != 0
    assert "no farm with reference F-99" in result.output


def test_a_field_on_a_lease_that_is_not_there_is_refused(
    growers: Callable[..., Result],
) -> None:
    growers("farm", "add", "F-3", "P-12", "Home Place")
    result = growers("field", "add", "FL-9", "F-3", "North 80", "--acres", "78.4", "--lease", "L-9")
    assert result.exit_code != 0
    assert "no lease with reference L-9" in result.output


def test_a_field_with_no_acres_in_it_is_refused(growers: Callable[..., Result]) -> None:
    growers("farm", "add", "F-3", "P-12", "Home Place")
    result = growers("field", "add", "FL-9", "F-3", "North 80", "--acres", "0", "--lease", "L-1")
    assert result.exit_code != 0
    assert "must be above zero" in result.output


def test_the_field_listing_totals_the_acres(growers: Callable[..., Result]) -> None:
    growers("farm", "add", "F-3", "P-12", "Home Place")
    growers("field", "add", "FL-9", "F-3", "North 80", "--acres", "78.4", "--lease", "L-1")
    growers("field", "add", "FL-2", "F-3", "Turnrow", "--acres", "30", "--lease", "L-1")
    assert "108.40" in growers("field", "list").output


def test_fields_can_be_listed_for_one_farm(growers: Callable[..., Result]) -> None:
    growers("farm", "add", "F-3", "P-12", "Home Place")
    growers("farm", "add", "F-7", "P-40", "River Place")
    growers("field", "add", "FL-9", "F-3", "North 80", "--acres", "78.4", "--lease", "L-1")
    output = growers("field", "list", "--farm", "F-7").output
    assert "FL-9" not in output
    assert "no fields yet" in output


def test_an_irrigated_field_is_marked(growers: Callable[..., Result]) -> None:
    growers("farm", "add", "F-3", "P-12", "Home Place")
    growers(
        "field",
        "add",
        "FL-9",
        "F-3",
        "North 80",
        "--acres",
        "78.4",
        "--lease",
        "L-1",
        "--irrigated",
    )
    assert "yes" in growers("field", "list").output


def test_the_farm_listing_counts_the_fields(growers: Callable[..., Result]) -> None:
    growers("farm", "add", "F-3", "P-12", "Home Place")
    growers("field", "add", "FL-9", "F-3", "North 80", "--acres", "78.4", "--lease", "L-1")
    assert "1" in growers("farm", "list").output
