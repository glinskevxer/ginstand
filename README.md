# ginstand

Office records for a custom cotton gin. Seed cotton arrives as modules, gets
ginned into bales, the bales get classed and valued against the commodity loan,
and the producer gets a settlement statement.

The gin does not own the cotton. It charges for ginning, buys the seed, and
hands the lint back. Most of the work in here is keeping straight whose cotton
is in which bale once a gin run has mixed four growers together, and being able
to show a producer the arithmetic afterwards.

## Getting started

```
pip install -e ".[dev]" -c constraints.txt
pytest -q
```

Stand a book up and gin something:

```
ginstand --book 2025.sqlite3 init --on 2025-08-04
ginstand --book 2025.sqlite3 producer add P-12 "Aldys Brothers" --ccc A4471
ginstand --book 2025.sqlite3 lease add L-1 P-12 --kind owner
ginstand --book 2025.sqlite3 farm add F-3 P-12 "Home Place"
ginstand --book 2025.sqlite3 field add FL-9 F-3 "North 80" --acres 78.4 --lease L-1
ginstand --book 2025.sqlite3 yard receive M-1 --field FL-9 \
  --harvested 2025-09-30 --received 2025-10-02 \
  --gross 56140 --tare 26140 --moisture 9.4 --wrap tarp
ginstand --book 2025.sqlite3 run open GR-1 --gin-code 41207 --on 2025-10-14
ginstand --book 2025.sqlite3 run feed-queue GR-1 --on 2025-10-14
ginstand --book 2025.sqlite3 run press GR-1 --on 2025-10-14 \
  --gross 512 --tare 22 --moisture 6.8 --count 34
ginstand --book 2025.sqlite3 run close GR-1 --on 2025-10-14 --allocate
ginstand --book 2025.sqlite3 settle register GR-1 --on 2025-11-03
```

The full command reference is in [docs/commands.md](docs/commands.md) and the
book's schema is in [docs/schema.md](docs/schema.md). The words and the numbers
the office argues about are in [docs/glossary.md](docs/glossary.md). All three
are generated and CI fails if they go stale.

## What is in here

| package | what it holds |
| --- | --- |
| `units` | weights, moisture, staple, money, and splitting a whole thing in proportion |
| `grades` | the colour chart and the extraneous matter codes |
| `model` | the records, as frozen dataclasses that check themselves |
| `store` | the sqlite book, its migrations, and one repository per record |
| `yard` | receiving modules, holding them, and deciding what gins next |
| `ginning` | runs, the press, turnout, allocation, seed and moisture restoration |
| `classing` | reading the classing file, filing it, and where a bale stands |
| `loan` | the published premium and discount tables, and what a bale is worth |
| `charges` | the ginning tariff and what a share of a run costs |
| `warehouse` | receipts and storage |
| `quality` | bale weight control at the press |
| `settle` | producer statements, the lease split, and the account ledger |
| `report` | the reports the office runs |
| `cli` | the command line |
| `tools` | the checks CI runs against this package |

## The rules worth knowing

A few things in here are not obvious and are the reason the code is shaped the
way it is.

**A run mixes producers, so its bales have to be divided.** The division is by
seed cotton weight, and because bales are whole, everybody is left owed a
fraction of one. That fraction is carried to their next run in the same crop
year rather than rounded away, so a producer's bale count on one run cannot be
checked without knowing what happened on the run before.

**The staple premium is keyed on the colour group.** A bale that classes a group
worse loses on the colour line and again on the staple line, because it moves to
a different staple ladder at the same time.

**The micronaire table is not monotonic.** The premium band sits in the middle,
at 3.7 to 4.2, with discounts on both sides and the steeper side underneath.

**The lease split runs on the settlement total, not on the lint.** A landlord on
a quarter share carries a quarter of the ginning charge, so changing a charge
moves their share.

**The yard queue is age multiplied by moisture above the safe line.** Neither
number on its own gives an order the gin manager agrees with: a dry module can
sit for a month and a wet one cannot sit for a week.

**A bale's weight is judged against its own run, not against the press
target.** A run of consistently light bales is under control and the press needs
looking at. One bale forty pounds off the run it came from is a bale that hung
up. The same 455 pound bale is unremarkable on one run and a finding on another.

**A statement is worked out and agreed in two steps.** Printing one does not
put it on the producer's account, because a figure gets queried before it gets
agreed, and a producer querying a number they have already been credited with is
a harder conversation than one they have not.

**Nothing reads the wall clock.** Every operation that needs to know what day it
is takes the day as an argument, which is what makes a settlement reproducible a
year later.

## Development

Everything CI runs, runs locally:

```
ruff check .
ruff format --check .
mypy
pytest -q
python -m ginstand.tools.check_docstrings
python -m ginstand.tools.check_clock
python -m ginstand.tools.check_layers
python -m ginstand.tools.check_migrations
python -m ginstand.tools.check_tests
python -m ginstand.tools.check_help
python -m ginstand.tools.check_wiring
python -m ginstand.tools.check_pins
python -m ginstand.tools.check_messages
python -m ginstand.tools.check_package
python -m ginstand.tools.schema_dump --check
python -m ginstand.tools.build_docs --check
python -m ginstand.tools.build_glossary --check
python -m ginstand.tools.smoke
```
