# Changelog

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
