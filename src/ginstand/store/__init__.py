"""The book: where the gin office's records are kept.

One sqlite file per crop year is how the office thinks about it, and this
package does not argue. A book is opened, read and written through repositories,
one per kind of record, and every repository hands back the frozen model objects
rather than rows.

Dates are stored as ISO strings and decimals as text. Neither is stored through
sqlite's type adapters: those are deprecated, they hide the conversion, and text
that a person can read in a database browser is worth more here than a byte or
two saved.
"""
