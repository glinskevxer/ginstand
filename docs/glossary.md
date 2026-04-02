# Glossary

This file is generated. Run `python -m ginstand.tools.build_glossary`
after adding or changing a documented constant, and CI will tell you if
you forgot.


## ginstand.charges.published

**SEED_PRICES** = `{2025: money('210.00'), 2026: money('225.00')}`

The contracted price for cottonseed, per ton.


## ginstand.classing.estimate

**GROUP_BANDS**

Upper bound of plus b for each group. Anything above the last is yellow stained.

**RANK_FLOORS**

Lowest Rd that still reaches each rank, best rank first. One ladder for every column. Reflectance means the same thing whatever the yellowness is, so the row does not move between columns. What moves is which rows exist: the yellow columns are short at the top, and a reading that would be rank 1 in white falls to the best rank its own column carries.


## ginstand.classing.ingest

**FIELDS**

Half open character ranges, counted from zero.

**RECORD_WIDTH** = `50`

Everything up to the remarks, which run to the end of the line.


## ginstand.classing.recheck

**CHASE_AFTER_DAYS** = `14`

A request out longer than this is one to ring the office about.

**GRADED**

The readings a recheck can change. Trash and remarks are not graded.


## ginstand.classing.standing

**CONDEMNING_PLASTIC** = `ExtraneousLevel.HEAVY`

The level of plastic this gin will not ship at any price.

**OffSchedule.COLOUR** = `'colour below grade'`

The card graded the colour rank eight.

**OffSchedule.LEAF** = `'leaf below grade'`

The card graded the leaf eight.

**OffSchedule.PLASTIC** = `'heavy plastic'`

The classer found plastic at the heavy level. This is the gin's own rule.


## ginstand.ginning.restore

**MAX_ADDED_FRACTION** = `Decimal('0.020')`

Water added may not exceed this fraction of the bale's weight at the press.


## ginstand.ginning.seed

**HIGH_SEED_TURNOUT** = `Decimal('0.5600')`

The band a run's seed turnout should land in. Outside it, a ticket is wrong.

**SEED_GRACE_DAYS** = `10`

How long after a run closes a seed load can still be booked against it.


## ginstand.ginning.turnout

**HIGH_TURNOUT** = `Decimal('0.4500')`

Above this the seed cotton weight is wrong, not the lint.

**LOW_TURNOUT** = `Decimal('0.2800')`

Below this the run either had wet cotton or a stand set badly.


## ginstand.grades.color

**CHART**

Which ranks the chart carries in each group.


## ginstand.ids

**REFERENCE_PATTERN** = `re.compile('^[A-Z0-9][A-Z0-9-]{0,22}[A-Z0-9]$')`

Two to twenty four characters, upper case, digits and inner dashes.


## ginstand.loan.schedule

**WHITE_FAMILY** = `(ColorGroup.WHITE, ColorGroup.LIGHT_SPOTTED)`

The colour groups that carry the better staple ladder.


## ginstand.loan.value

**MINIMUM_RATE** = `Decimal('0.0000')`

A bale is never worth a negative amount, however far the discounts run.


## ginstand.model.account

**EntryKind.ADJUSTMENT** = `'adjustment'`

A correction after the fact: a weight found wrong, a charge missed.

**EntryKind.PAYMENT** = `'payment'`

Money that actually moved.

**EntryKind.SETTLEMENT** = `'settlement'`

What a run came to for this producer.


## ginstand.model.bale

**MAX_BALE_POUNDS** = `750`

Past this the press did not release, or two cycles were weighed together.

**MAX_TARE_POUNDS** = `40`

Bagging and eight ties. Outside this range the tare was typed wrong.

**MIN_BALE_POUNDS** = `300`

A press cycle that produced less than this did not make a saleable bale.


## ginstand.model.farm

**MAX_FIELD_ACRES** = `Decimal('5000')`

Bigger than this is a farm typed into a field record.


## ginstand.model.hold

**HoldReason.CONTAMINATION** = `'contamination'`

Something else in the module: twine, a jacket, a piece of the picker.

**HoldReason.IDENTITY** = `'identity'`

The tag does not match the paperwork. Ginning it loses whose it was.

**HoldReason.PLASTIC** = `'plastic'`

Wrap damage. It gets picked over before it goes anywhere near a stand.

**HoldReason.WEIGHT** = `'weight'`

The ticket is disputed and the module is not ginned until it is settled.

**HoldReason.WET** = `'wet'`

Over the dryer's range. It goes back out to lose moisture.


## ginstand.model.module

**MAX_MODULE_POUNDS** = `60000`

Heavier than this is two modules weighed as one.

**MIN_MODULE_POUNDS** = `500`

Lighter than this is a partial load or a scale that did not settle.

**ModuleKind.RECTANGULAR** = `'rectangular'`

Off a module builder, tarped rather than wrapped.

**ModuleKind.ROUND** = `'round'`

Off a round module picker, wrapped in plastic film.

**ModuleKind.TRAILER** = `'trailer'`

Loose in a trailer. Older kit, and it still turns up.


## ginstand.model.producer

**LeaseKind.CASH** = `'cash'`

The landlord is paid rent in cash and takes none of the crop.

**LeaseKind.OWNER** = `'owner'`

The producer farms their own ground. Nothing is split.

**LeaseKind.SHARE** = `'share'`

The landlord takes a fraction of the settlement. A quarter is usual.


## ginstand.model.recheck

**RecheckOutcome.CHANGED** = `'changed'`

The office issued a different card.

**RecheckOutcome.OPEN** = `'open'`

Sent, and nothing has come back.

**RecheckOutcome.REFUSED** = `'refused'`

The office would not look, usually because the sample was gone.

**RecheckOutcome.UNCHANGED** = `'unchanged'`

The office read the same sample the same way.

**SAMPLE_HELD_DAYS** = `28`

How long the office keeps a sample after it classes it.


## ginstand.quality.tolerance

**BALE_TOLERANCE** = `40`

How far a bale may sit from its own run's mean before it is worth a look.

**MINIMUM_BALES** = `5`

Below this a run's mean is not a mean, so bales are measured on the target.

**RUN_TOLERANCE** = `30`

How far a run's mean may sit from the target before the press is queried.

**TARGET_POUNDS** = `500`

What the press is set to make.


## ginstand.report.audit

**LONG_RUN_DAYS** = `7`

A run open longer than this is one somebody forgot to close.

**Severity.FAULT** = `'fault'`

The book says two things that cannot both be true.

**Severity.QUERY** = `'query'`

Worth a look. Usually a run still in progress.


## ginstand.season

**CROP_YEAR_START_MONTH** = `8`

August. The crop year is named for the calendar year its August falls in.


## ginstand.units.moisture

**DRYER_THRESHOLD** = `Decimal('8.0')`

Seed cotton above this goes through the dryers before the stands.

**DRY_GINNING_FLOOR** = `Decimal('5.0')`

Below this the fibre breaks at the gin stand and the staple reading drops.

**MAX_MOISTURE** = `Decimal('25.0')`

A meter reading past this is a wet spot or a fault, not a module.

**SAFE_BALE_MOISTURE** = `Decimal('7.5')`

Above this a bale heats in the warehouse. It is the ceiling on restoration.


## ginstand.units.staple

**LONGEST_STAPLE** = `48`

An inch and a half. Above this the reading is an instrument fault.

**SHORTEST_STAPLE** = `24`

Three quarters of an inch. Below this the sample is not upland cotton.


## ginstand.units.weight

**MAX_TICKET_POUNDS** = `200000`

Refuse anything past a loaded truck and trailer. A scale that reads higher than this has a fault, and a fault read into the book is worse than a refusal.

**POUNDS_PER_CWT** = `100`

Hundredweight. The ginning tariff and the seed contract both price per cwt.


## ginstand.yard.holds

**HOLD_MOISTURE** = `Decimal('14.0')`

Past the dryers' range. A module this wet goes back out rather than through.


## ginstand.yard.order

**RISK_LIMIT** = `Decimal('30.0')`

Point days past which a module has to gin before anything comfortable does.

**SAFE_YARD_MOISTURE** = `Decimal('8.0')`

At or below this a module can sit. Above it, every day costs something.
