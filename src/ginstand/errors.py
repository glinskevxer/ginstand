"""The error types the whole package raises.

Every failure a caller can reasonably be expected to handle is one of these.
Anything else escaping is a bug in this package, not bad input, and it is left
alone so it shows up in a traceback rather than being turned into a message.

The command line catches :class:`GinstandError` and prints ``str(exc)``, so the
message text is user facing. Write it for the gin office, not for a programmer:
say what was wrong with the input and what was expected instead.
"""

from __future__ import annotations


class GinstandError(Exception):
    """Base for everything this package raises on purpose."""


class ValidationError(GinstandError):
    """A value did not meet the rule stated for its field.

    Carries the field name so a caller collecting several failures can say
    which input each one came from.
    """

    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"{field}: {message}")
        self.field = field
        self.message = message


class NotFoundError(GinstandError):
    """A record was looked up by key and is not in the book."""

    def __init__(self, kind: str, key: str) -> None:
        super().__init__(f"no {kind} with reference {key}")
        self.kind = kind
        self.key = key


class DuplicateError(GinstandError):
    """A record was added under a key that is already taken."""

    def __init__(self, kind: str, key: str) -> None:
        super().__init__(f"{kind} {key} is already in the book")
        self.kind = kind
        self.key = key


class StateError(GinstandError):
    """The operation is fine in general but not against this record's state.

    Feeding a module into a closed gin run, pressing a bale on a run that never
    opened, classing a bale twice: all of them land here.
    """


class ScheduleError(GinstandError):
    """A premium or discount schedule could not price the classing given."""
