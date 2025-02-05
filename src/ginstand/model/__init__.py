"""The records the gin office keeps.

Every record in here is a frozen dataclass that checks itself on construction.
An invalid record cannot exist: there is no half built state to guard against
later, and a record read back out of the book is as trustworthy as one that was
just typed in.

Records hold references to other records as strings, never as objects. The store
layer is what turns a reference into a record, and keeping the records free of
each other is what lets one be loaded without dragging the book in behind it.
"""
