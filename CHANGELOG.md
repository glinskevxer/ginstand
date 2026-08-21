# Changelog

## 1.0.0

A season's worth of the things the first release did not cover, and the checks
that stop them going stale.

- Recheck requests against a classing card, closed by comparing the card that
  came back rather than by being told what happened to it.
- A producer account: settlements, adjustments and payments in one ledger, with
  a statement worked out and agreed in two steps rather than one.
- Closing a crop year, which pays out the fractions of a bale carried through
  the season at the season's own mean weight and rate.
- Bale weight control at two levels, and a check weigh sampling table where the
  run's size picks the sample and the sample picks what fails.
- Instrument calibration as a log, so a ticket from October can be asked about
  in February, and an audit fault for tickets written on a scale nobody vouched
  for.
- A downtime log, with bales an hour worked out over the time the gin ran.
- The yard map: rows worked from one end, and both the order the cotton wants
  and the order the yard can feed.
- Bulk intake off the weighbridge file, keeping the rows that will not go in.
- Reports for fields, varieties, plastic, moisture, the day sheet, the warehouse
  position, the recheck rate and two crop years side by side.
- Export to CSV and back again, a backup through sqlite's own, a search across
  every register, and one page in the morning that says what to look at.
- Sixteen checks CI runs against this package, a generated command reference,
  schema and glossary, and a design note whose named code is checked.
- The arithmetic laws written down as code and run over a spread of inputs.

Three defects fixed that the tests did not find. The colour chart was sitting a
layer above the records that read it, which the layer check found. Every
`with connect(...)` was leaking a connection, because a sqlite connection is a
context manager for its transaction and not for itself. And five fixtures opened
a book and never closed it. The last two were found by running the suite on
Python 3.13, where an unclosed connection warns and 3.12 says nothing, and both
now have a check behind them.

## 0.1.0

First working season end to end.

- Producers, leases, farms and fields, with a producer's cotton traced back to
  the field it came off.
- Module yard: weighing in, holds with a person on them, and a ginning queue
  ordered by age multiplied by moisture above the safe line.
- Gin runs: one open at a time, feeding checked five ways, a press that takes
  its bale numbers out of the book, turnout final only once the run is closed.
- Bale allocation by seed cotton weight, with the fraction each producer is
  owed carried to their next run in the same crop year.
- Cottonseed booked by the truckload, with a grace after the run closes.
- Moisture restoration capped by the storage ceiling and by a fraction of the
  bale's weight at the press.
- Classing: the colour chart, extraneous matter codes, a fixed width classing
  file reader that keeps its bad records, and filing that goes card by card.
- Commodity loan valuation off five published tables, with the working kept.
- Ginning tariff charged against the basis each line names.
- Warehouse receipts as documents of title, and storage billed against a
  contract whose minimum is a floor under the days charged.
- Producer settlements, provisional until the last card arrives, split on the
  settlement total by lease.
- Reports: yard standing, ginning queue, holds, run sheet, quality, loan
  register, settlement register and season summary.
- A command line over all of it, and eleven checks CI runs against this package.
