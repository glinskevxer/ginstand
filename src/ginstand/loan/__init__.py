"""The loan schedule: what a bale is worth against the commodity loan.

A bale's loan value is a base rate for the crop year, in cents per pound,
adjusted by premiums and discounts read off published tables. The tables are
keyed on the classing, so a bale's value is entirely decided by the card except
for its weight.

Everything in here is in points. A point is one hundredth of a cent per pound.
On a five hundred pound bale a point is five cents, and on a hundred bale lot it
is five dollars, so the tables are published to the point and the arithmetic
keeps them there until the last step.
"""
