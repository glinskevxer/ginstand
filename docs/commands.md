# Commands

This file is generated. Run `python -m ginstand.tools.build_docs` after
changing a command, and CI will tell you if you forgot.

Every command takes `--book` on the top level command, and every command
that needs a date takes it as an argument. Nothing reads the clock.

## init

Stand up a new book.

```
ginstand init
```

- `--on` — the day the book was opened (required)

## about

Say what this book is and what version wrote it.

```
ginstand about
```

## producer

The producer register.

### producer add

Put a producer in the book.

```
ginstand producer add <ref> <name>
```

- `--address` — postal address
- `--phone` — telephone number
- `--ccc` — loan farm number, if enrolled

### producer list

Every producer in the book.

```
ginstand producer list
```

### producer show

One producer, with their farms and leases.

```
ginstand producer show <ref>
```

## lease

The lease register.

### lease add

Put a lease in the book.

```
ginstand lease add <ref> <tenant>
```

- `--kind` — how the crop is divided (required)
- `--landlord` — the landlord's producer reference
- `--share` — the landlord's share

### lease list

Every lease in the book.

```
ginstand lease list
```

## farm

The farm register.

### farm add

Put a farm in the book.

```
ginstand farm add <ref> <producer> <name>
```

- `--fsa` — the farm agency number
- `--county` — the county the farm is in

### farm list

Every farm in the book, or one producer's.

```
ginstand farm list
```

- `--producer` — only this producer's farms

## field

The field register.

### field add

Put a field in the book.

```
ginstand field add <ref> <farm_ref> <name>
```

- `--acres` — acres in the field (required)
- `--lease` — the lease this field is farmed under (required)
- `--variety` — the variety planted
- `--irrigated` — the field is irrigated

### field list

Every field in the book, or one farm's.

```
ginstand field list
```

- `--farm` — only this farm's fields

## yard

The module yard.

### yard receive

Weigh a module in.

```
ginstand yard receive <tag>
```

- `--field` — the field it came off (required)
- `--kind` — how the module was made
- `--wrap` — what is around it
- `--harvested` — the day it was picked (required)
- `--received` — the day it crossed the scale (required)
- `--gross` — gross weight in pounds (required)
- `--tare` — tare weight in pounds (required)
- `--moisture` — moisture percent (required)
- `--variety` — the variety, if it differs from the field
- `--note` — anything the scale operator wants recorded

### yard show

One module, with where it stands in the yard.

```
ginstand yard show <tag>
```

- `--on` — the day to work the standing out at (required)

### yard hold

Hold a module so it does not gin.

```
ginstand yard hold <tag>
```

- `--reason` — why the module is being held (required)
- `--on` — the day the hold is placed (required)
- `--by` — who placed it
- `--note` — anything worth recording

### yard lift

Take the hold off a module.

```
ginstand yard lift <tag>
```

- `--on` — the day the hold is lifted (required)
- `--by` — who lifted it

### yard standing

Everything unginned, worst first.

```
ginstand yard standing
```

- `--on` — the day to work it out at (required)

### yard queue

The order the yard should feed.

```
ginstand yard queue
```

- `--on` — the day to work it out at (required)
- `--no-group` — do not keep a producer's modules together

### yard holds

Everything the yard is holding.

```
ginstand yard holds
```

- `--on` — the day to count the days held to (required)

## run

Gin runs.

### run open

Open a run. Only one can be open at a time.

```
ginstand run open <ref>
```

- `--gin-code` — the five digit classing office code (required)
- `--on` — the day the run opens (required)
- `--shift` — which shift is on
- `--note` — anything worth recording

### run feed

Feed modules into a run, in the order given.

```
ginstand run feed <ref> <modules>...
```

- `--on` — the day they go on the stands (required)

### run feed-queue

Feed whatever the yard queue says should gin next.

```
ginstand run feed-queue <ref>
```

- `--on` — the day they go on the stands (required)
- `--limit` — feed at most this many modules

### run press

Take bales off the press.

```
ginstand run press <ref>
```

- `--on` — the day the bale came off (required)
- `--gross` — gross weight in pounds (required)
- `--tare` — bagging and ties in pounds (required)
- `--moisture` — moisture at the press (required)
- `--stand` — which stand it came off
- `--count` — how many bales

### run restore

The wettest a bale of this weight may be taken to.

```
ginstand run restore
```

- `--pressed` — the bale's weight at the press (required)
- `--from` — moisture now (required)

### run close

Close a run so its turnout is final.

```
ginstand run close <ref>
```

- `--on` — the day the run closes (required)
- `--allocate` — allocate the bales as well

### run seed

Book a truckload of cottonseed against a run.

```
ginstand run seed <ref>
```

- `--on` — the day the load was weighed (required)
- `--pounds` — net weight of the load (required)
- `--ticket` — the seed house ticket number
- `--buyer` — who took it

### run allocate

Give a closed run's bales to the producers who fed it.

```
ginstand run allocate <ref>
```

- `--on` — the day the allocation is made (required)
- `--dry-run` — work it out without writing it

### run sheet

The run sheet.

```
ginstand run sheet <ref>
```

- `--feed-only` — just the feed sheet
- `--bales-only` — just the bale list

### run current

Which run is open, if any.

```
ginstand run current
```

## card

Classing cards.

### card file

Read a classing file and file it against the bales.

```
ginstand card file <path>
```

- `--recheck` — this file replaces cards already filed
- `--dry-run` — read the file without filing it

### card show

One bale's card, and where it stands against the schedule.

```
ginstand card show <tag>
```

### card list

Every card filed, or one run's.

```
ginstand card list
```

- `--run` — only bales off this run

### card outstanding

Every bale still waiting on a card.

```
ginstand card outstanding
```

### card estimate

What the gin's own instrument would call this sample.

```
ginstand card estimate
```

- `--rd` — reflectance off the colorimeter (required)
- `--plus-b` — yellowness off the colorimeter (required)

## recheck

Recheck requests against a classing card.

### recheck ask

Ask the office to read a sample again.

```
ginstand recheck ask <tag>
```

- `--reason` — what the gin thinks is wrong (required)
- `--on` — the day the request is sent (required)
- `--by` — who asked
- `--note` — anything worth recording

### recheck settle

Answer an open request by hand.

```
ginstand recheck settle <tag>
```

- `--outcome` — what the office said (required)
- `--on` — the day the answer came back (required)
- `--note` — anything worth recording

### recheck list

Every request the office still has.

```
ginstand recheck list
```

- `--on` — the day to count the days out to (required)
- `--chase` — only the ones out too long

### recheck history

Every request ever made against one bale.

```
ginstand recheck history <tag>
```

## loan

The commodity loan schedule.

### loan value

What one bale is worth against the loan.

```
ginstand loan value <tag>
```

- `--working` — print every line of the working

### loan lot

What a producer's classed bales are worth against the loan.

```
ginstand loan lot <producer>
```

- `--crop-year` — the crop year to value (required)

### loan schedule

One of the published premium and discount tables.

```
ginstand loan schedule
```

- `--crop-year` — which year's tables (required)
- `--table` — which table to print

### loan register

Every classed bale in a crop year, with what the loan pays.

```
ginstand loan register
```

- `--crop-year` — the crop year to price (required)

## warehouse

Warehouses and the receipts they issue.

### warehouse add

Put a warehouse in the book.

```
ginstand warehouse add <ref> <name>
```

- `--code` — the licensed warehouse code
- `--location` — where it is

### warehouse list

Every warehouse, with what it is holding.

```
ginstand warehouse list
```

## receipt

Warehouse receipts.

### receipt issue

Put bales into store and issue their receipts.

```
ginstand receipt issue <tags>...
```

- `--warehouse` — which warehouse (required)
- `--on` — the day it goes into store (required)
- `--holder` — who holds it, if not the owner

### receipt release

Take a bale back out of store.

```
ginstand receipt release <number>
```

- `--on` — the day it comes out (required)

### receipt transfer

Move a receipt into somebody else's hands.

```
ginstand receipt transfer <number> <to_holder>
```

### receipt list

Receipts, outstanding by default.

```
ginstand receipt list
```

- `--holder` — only this holder's receipts
- `--warehouse` — only this warehouse
- `--all` — released receipts as well

### receipt storage

What somebody owes the warehouse.

```
ginstand receipt storage <who>
```

- `--on` — the day to bill up to (required)
- `--crop-year` — which contract applies (required)

## settle

Settlement.

### settle statement

One producer's statement for one run.

```
ginstand settle statement <run_ref> <producer>
```

- `--on` — the day the statement is issued (required)
- `--extra` — an optional charge code to bill

### settle register

Every producer on a run, with what they are owed.

```
ginstand settle register <run_ref>
```

- `--on` — the day the register is run (required)

### settle check

Check a run's settlement against the run's own figures.

```
ginstand settle check <run_ref>
```

- `--on` — the day to check at (required)

### settle shares

What each producer has on a run, before any money is worked out.

```
ginstand settle shares <run_ref>
```

### settle tariff

The published ginning tariff for a crop year.

```
ginstand settle tariff
```

- `--crop-year` — which year's rates (required)

## report

The reports the office runs.

### report season

A crop year's totals.

```
ginstand report season
```

- `--crop-year` — which crop year (required)
- `--runs` — add the run by run table
- `--producers` — add the producer table

### report runs

Every run in a crop year, with what it turned out.

```
ginstand report runs
```

- `--crop-year` — which crop year (required)

### report producers

Every producer in a crop year, with what they put in and took out.

```
ginstand report producers
```

- `--crop-year` — which crop year (required)

### report quality

How a crop year classed.

```
ginstand report quality
```

- `--crop-year` — which crop year (required)
- `--table` — which part of the quality report

### report audit

Read the whole book looking for things that cannot be true.

```
ginstand report audit
```

- `--on` — the day to audit at (required)
- `--faults-only` — leave out the queries

### report rechecks

How the rechecks the gin asked for turned out.

```
ginstand report rechecks
```

- `--on` — the day to work turnaround to (required)

### report book

What the whole book holds, one line per register.

```
ginstand report book
```
