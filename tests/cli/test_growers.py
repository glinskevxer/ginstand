"""The producer and lease commands."""

from __future__ import annotations

from collections.abc import Callable

from click.testing import Result


def test_a_producer_can_be_added_and_listed(gin: Callable[..., Result]) -> None:
    assert gin("producer", "add", "p-12", "Aldys Brothers").exit_code == 0
    listing = gin("producer", "list")
    assert "P-12" in listing.output
    assert "Aldys Brothers" in listing.output


def test_an_empty_register_says_so(gin: Callable[..., Result]) -> None:
    assert "no producers yet" in gin("producer", "list").output


def test_adding_the_same_producer_twice_is_refused(gin: Callable[..., Result]) -> None:
    gin("producer", "add", "P-12", "Aldys Brothers")
    result = gin("producer", "add", "P-12", "Somebody Else")
    assert result.exit_code != 0
    assert "already in the book" in result.output


def test_a_producer_without_a_name_is_refused(gin: Callable[..., Result]) -> None:
    result = gin("producer", "add", "P-12", "   ")
    assert result.exit_code != 0
    assert "producer name" in result.output


def test_the_loan_number_shows_on_the_listing(gin: Callable[..., Result]) -> None:
    gin("producer", "add", "P-12", "Aldys Brothers", "--ccc", "A4471")
    assert "yes" in gin("producer", "list").output


def test_show_reads_the_whole_record(gin: Callable[..., Result]) -> None:
    gin("producer", "add", "P-12", "Aldys Brothers", "--phone", "555 0143")
    output = gin("producer", "show", "p-12").output
    assert "Aldys Brothers" in output
    assert "555 0143" in output
    assert "not enrolled" in output


def test_showing_a_producer_who_is_not_there_says_so(gin: Callable[..., Result]) -> None:
    result = gin("producer", "show", "P-99")
    assert result.exit_code != 0
    assert "no producer with reference P-99" in result.output


def test_an_owner_lease_can_be_added(gin: Callable[..., Result]) -> None:
    gin("producer", "add", "P-12", "Aldys Brothers")
    result = gin("lease", "add", "L-1", "P-12", "--kind", "owner")
    assert result.exit_code == 0
    assert "added lease L-1" in result.output


def test_a_share_lease_carries_the_landlord_and_share(gin: Callable[..., Result]) -> None:
    gin("producer", "add", "P-12", "Aldys Brothers")
    gin("producer", "add", "P-40", "Merrick Land Co")
    gin(
        "lease",
        "add",
        "L-2",
        "P-12",
        "--kind",
        "share",
        "--landlord",
        "P-40",
        "--share",
        "0.25",
    )
    output = gin("lease", "list").output
    assert "L-2" in output
    assert "P-40" in output
    assert "0.25" in output


def test_a_share_lease_without_a_landlord_is_refused(gin: Callable[..., Result]) -> None:
    gin("producer", "add", "P-12", "Aldys Brothers")
    result = gin("lease", "add", "L-2", "P-12", "--kind", "share", "--share", "0.25")
    assert result.exit_code != 0
    assert "share lease needs a landlord" in result.output


def test_a_lease_kind_that_does_not_exist_is_refused(gin: Callable[..., Result]) -> None:
    gin("producer", "add", "P-12", "Aldys Brothers")
    result = gin("lease", "add", "L-2", "P-12", "--kind", "handshake")
    assert result.exit_code != 0


def test_the_show_command_lists_a_producers_leases(gin: Callable[..., Result]) -> None:
    gin("producer", "add", "P-12", "Aldys Brothers")
    gin("lease", "add", "L-1", "P-12", "--kind", "owner")
    assert "L-1" in gin("producer", "show", "P-12").output


def test_an_empty_lease_register_says_so(gin: Callable[..., Result]) -> None:
    assert "no leases yet" in gin("lease", "list").output


def test_an_edit_changes_only_what_was_given(gin: Callable[..., Result]) -> None:
    gin("producer", "add", "P-12", "Aldys Brothers", "--phone", "555 0143")
    result = gin("producer", "edit", "P-12", "--name", "Aldys Bros")
    assert result.exit_code == 0
    assert "changed producer P-12 Aldys Bros" in result.output
    output = gin("producer", "show", "P-12").output
    assert "555 0143" in output


def test_an_edit_that_changes_nothing_says_so(gin: Callable[..., Result]) -> None:
    gin("producer", "add", "P-12", "Aldys Brothers")
    assert "is unchanged" in gin("producer", "edit", "P-12").output


def test_editing_somebody_who_is_not_there_is_refused(
    gin: Callable[..., Result],
) -> None:
    result = gin("producer", "edit", "P-99", "--name", "Nobody")
    assert result.exit_code != 0
    assert "no producer with reference P-99" in result.output


def test_an_edit_can_enrol_a_producer_for_the_loan(gin: Callable[..., Result]) -> None:
    gin("producer", "add", "P-12", "Aldys Brothers")
    gin("producer", "edit", "P-12", "--ccc", "A4471")
    assert "yes" in gin("producer", "list").output
