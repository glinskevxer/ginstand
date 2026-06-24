# Why this is shaped the way it is

Most of this package is ordinary. Records check themselves, a store reads and
writes them, a rule layer sits on top and a command line sits on that. What is
worth writing down is the handful of places where the obvious design is wrong,
and why.

Every rule below names the module it lives in, and CI checks those modules and
names still exist. A design note that describes code that has moved is worse
than none.

## The carry, in `ginstand.ginning.shares`

A gin run mixes cotton from several producers and presses whole bales, so every
run leaves each producer owed a fraction of one. The obvious design rounds that
away. This one carries it to their next run in the same crop year, which means a
producer's bale count on one run cannot be checked without knowing what happened
on the run before, and at the end of the year the fractions are paid out in lint
at the season's own mean weight and rate.

`split_bales` does the division. `ginstand.settle.close.close` pays what is left.

## The staple ladder, in `ginstand.loan.schedule`

A bale's staple premium is not a property of its staple. The schedule keys the
staple table on the colour group, so a bale that classes a group worse loses on
the colour line and again on the staple line. `staple_ladder` picks the ladder
and `staple_points` reads it.

## Two rules for below grade, in `ginstand.classing.standing`

Colour rank eight and leaf grade eight are the classing office's judgement.
Heavy plastic is ours. `standing_of` keeps them apart, because a bale off the
schedule for our reason can be argued about internally and one off for the
office's reason cannot, and a settlement that cannot say which happened is one
nobody can answer questions about.

## The yard queue, in `ginstand.yard.order`

Age multiplied by moisture above the safe line, not either on its own. A dry
module can sit for a month and a wet one cannot sit for a week, so `spoil_points`
multiplies them and the moisture decides what the age is worth.

## Two orders for the same yard, in `ginstand.yard.places`

A row is worked from one end, so the order the cotton wants and the order the
yard can feed are different. `queue` gives the first and `row_order` gives the
second, and `digging` counts how far apart they are. This package does not have
an opinion about whether a spoiling module is worth an hour of loader time.

## Bale weight, judged twice, in `ginstand.quality.tolerance`

The run is measured against the press target and each bale against its own run's
mean, so the same 455 pound bale is unremarkable on one run and a finding on
another. `control_for` does both, and a run too short to have a mean is measured
on the target instead.

## The sampling table, in `ginstand.quality.sampling`

The run's size picks the sample size and the sample size picks the number of bad
bales that fails it. Neither number means anything without the other, which is
why `plan_for` returns them together rather than as two lookups.

## Downtime as a denominator, in `ginstand.ginning.downtime`

Bales an hour is worked out over the time the gin was actually running, so
`efficiency` takes the logged stops off the scheduled minutes. Writing a stop
down therefore makes the gin look faster, which is the incentive the log needs
to have if anybody is going to keep it.

## Calibration as a log, in `ginstand.quality.calibration`

`standing_on` answers what an instrument's state was on a given day, which is
the question a ticket from October raises in February. A flag would answer a
different question. A failed check vouches for nothing, including the days
before it, because nobody knows when the drift started.

## The lease split, in `ginstand.settle.share`

`split_settlement` divides the settlement total and not the lint, so a landlord
on a quarter share carries a quarter of the ginning charge. One side is rounded
and the other is the remainder, so the two always add back.

## Nothing reads the clock

Every operation that needs to know what day it is takes the day as an argument.
`ginstand.tools.check_clock` enforces it. That is what makes a settlement
reproducible a year later and what lets the tests run on any day of the year.
