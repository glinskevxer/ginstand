# The book

Schema version 13, built by 13 migrations.

This file is generated. Run `python -m ginstand.tools.schema_dump` after
adding a migration, and CI will tell you if you forgot.

## Migrations

1. producers, leases, farms and fields
2. the module yard and the gin run
3. bales and the classing cards against them
4. yard holds
5. bale allocation and the carry it leaves
6. cottonseed loads off a run
7. warehouses and the receipts they issue
8. recheck requests against a classing card
9. the producer account ledger
10. closing a crop year
11. instruments and their calibration log
12. where a module is standing in the yard
13. the downtime log against a run

## Tables

### account_entry

```sql
CREATE TABLE account_entry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    producer TEXT NOT NULL REFERENCES producer(ref),
    crop_year INTEGER NOT NULL,
    made TEXT NOT NULL,
    kind TEXT NOT NULL,
    amount INTEGER NOT NULL,
    run TEXT REFERENCES gin_run(ref),
    reference TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT ''
)
```

- `CREATE INDEX account_entry_by_producer ON account_entry(producer, crop_year, made)`

- `CREATE UNIQUE INDEX account_entry_one_settlement ON account_entry(producer, run) WHERE kind = 'settlement'`

### allocation_carry

```sql
CREATE TABLE allocation_carry (
    producer TEXT NOT NULL REFERENCES producer(ref),
    crop_year INTEGER NOT NULL,
    carry TEXT NOT NULL,
    PRIMARY KEY (producer, crop_year)
)
```

### bale

```sql
CREATE TABLE bale (
    tag TEXT PRIMARY KEY,
    run TEXT NOT NULL REFERENCES gin_run(ref),
    pressed TEXT NOT NULL,
    gross_pounds INTEGER NOT NULL,
    tare_pounds INTEGER NOT NULL,
    moisture_pct TEXT NOT NULL,
    stand TEXT NOT NULL DEFAULT ''
)
```

- `CREATE INDEX bale_by_pressed ON bale(pressed)`

- `CREATE INDEX bale_by_run ON bale(run)`

### bale_allocation

```sql
CREATE TABLE bale_allocation (
    tag TEXT PRIMARY KEY REFERENCES bale(tag),
    producer TEXT NOT NULL REFERENCES producer(ref),
    run TEXT NOT NULL REFERENCES gin_run(ref),
    allocated TEXT NOT NULL
)
```

- `CREATE INDEX bale_allocation_by_producer ON bale_allocation(producer)`

- `CREATE INDEX bale_allocation_by_run ON bale_allocation(run)`

### calibration

```sql
CREATE TABLE calibration (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument TEXT NOT NULL REFERENCES instrument(ref),
    checked TEXT NOT NULL,
    by_whom TEXT NOT NULL DEFAULT '',
    error TEXT NOT NULL,
    passed INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT ''
)
```

- `CREATE INDEX calibration_by_instrument ON calibration(instrument, checked)`

### classing

```sql
CREATE TABLE classing (
    tag TEXT PRIMARY KEY REFERENCES bale(tag),
    classed TEXT NOT NULL,
    color INTEGER NOT NULL,
    leaf INTEGER NOT NULL,
    staple INTEGER NOT NULL,
    micronaire TEXT NOT NULL,
    strength TEXT NOT NULL,
    uniformity TEXT NOT NULL,
    trash_pct TEXT NOT NULL,
    extraneous TEXT NOT NULL DEFAULT '',
    office TEXT NOT NULL DEFAULT '',
    remarks TEXT NOT NULL DEFAULT ''
)
```

- `CREATE INDEX classing_by_classed ON classing(classed)`

### crop_year_close

```sql
CREATE TABLE crop_year_close (
    crop_year INTEGER PRIMARY KEY,
    closed_on TEXT NOT NULL,
    bale_weight INTEGER NOT NULL,
    rate TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT ''
)
```

### downtime

```sql
CREATE TABLE downtime (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run TEXT NOT NULL REFERENCES gin_run(ref),
    stopped TEXT NOT NULL,
    started INTEGER NOT NULL,
    minutes INTEGER NOT NULL,
    reason TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT ''
)
```

- `CREATE INDEX downtime_by_run ON downtime(run, stopped, started)`

### farm

```sql
CREATE TABLE farm (
    ref TEXT PRIMARY KEY,
    producer TEXT NOT NULL REFERENCES producer(ref),
    name TEXT NOT NULL,
    fsa_number TEXT NOT NULL DEFAULT '',
    county TEXT NOT NULL DEFAULT ''
)
```

- `CREATE INDEX farm_by_producer ON farm(producer)`

### field

```sql
CREATE TABLE field (
    ref TEXT PRIMARY KEY,
    farm TEXT NOT NULL REFERENCES farm(ref),
    name TEXT NOT NULL,
    acres TEXT NOT NULL,
    lease TEXT NOT NULL REFERENCES lease(ref),
    variety TEXT NOT NULL DEFAULT '',
    irrigated INTEGER NOT NULL DEFAULT 0
)
```

- `CREATE INDEX field_by_farm ON field(farm)`

### gin_run

```sql
CREATE TABLE gin_run (
    ref TEXT PRIMARY KEY,
    crop_year INTEGER NOT NULL,
    gin_code TEXT NOT NULL,
    opened TEXT NOT NULL,
    closed TEXT,
    shift TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT ''
)
```

- `CREATE INDEX gin_run_by_crop_year ON gin_run(crop_year)`

### instrument

```sql
CREATE TABLE instrument (
    ref TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    description TEXT NOT NULL,
    serial TEXT NOT NULL DEFAULT '',
    retired TEXT
)
```

### lease

```sql
CREATE TABLE lease (
    ref TEXT PRIMARY KEY,
    tenant TEXT NOT NULL REFERENCES producer(ref),
    kind TEXT NOT NULL,
    landlord TEXT NOT NULL DEFAULT '',
    landlord_share TEXT NOT NULL DEFAULT '0'
)
```

- `CREATE INDEX lease_by_tenant ON lease(tenant)`

### module

```sql
CREATE TABLE module (
    tag TEXT PRIMARY KEY,
    field TEXT NOT NULL REFERENCES field(ref),
    kind TEXT NOT NULL,
    harvested TEXT NOT NULL,
    received TEXT NOT NULL,
    gross_pounds INTEGER NOT NULL,
    tare_pounds INTEGER NOT NULL,
    moisture_pct TEXT NOT NULL,
    wrap TEXT NOT NULL DEFAULT 'none',
    variety TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT ''
)
```

- `CREATE INDEX module_by_field ON module(field)`

- `CREATE INDEX module_by_received ON module(received)`

### producer

```sql
CREATE TABLE producer (
    ref TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    ccc_number TEXT NOT NULL DEFAULT ''
)
```

### receipt

```sql
CREATE TABLE receipt (
    number TEXT PRIMARY KEY,
    tag TEXT NOT NULL UNIQUE REFERENCES bale(tag),
    warehouse TEXT NOT NULL REFERENCES warehouse(ref),
    holder TEXT NOT NULL REFERENCES producer(ref),
    issued TEXT NOT NULL,
    released TEXT,
    note TEXT NOT NULL DEFAULT ''
)
```

- `CREATE INDEX receipt_by_holder ON receipt(holder)`

- `CREATE INDEX receipt_by_warehouse ON receipt(warehouse)`

### recheck

```sql
CREATE TABLE recheck (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tag TEXT NOT NULL REFERENCES bale(tag),
    requested TEXT NOT NULL,
    reason TEXT NOT NULL,
    requested_by TEXT NOT NULL DEFAULT '',
    settled TEXT,
    outcome TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT ''
)
```

- `CREATE INDEX recheck_by_tag ON recheck(tag)`

- `CREATE UNIQUE INDEX recheck_one_open ON recheck(tag) WHERE settled IS NULL`

### run_module

```sql
CREATE TABLE run_module (
    run TEXT NOT NULL REFERENCES gin_run(ref),
    module TEXT NOT NULL REFERENCES module(tag),
    position INTEGER NOT NULL,
    fed_on TEXT NOT NULL,
    PRIMARY KEY (run, module)
)
```

- `CREATE UNIQUE INDEX run_module_once ON run_module(module)`

- `CREATE UNIQUE INDEX run_module_position ON run_module(run, position)`

### schema_migration

```sql
CREATE TABLE schema_migration (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_on TEXT NOT NULL
)
```

### seed_load

```sql
CREATE TABLE seed_load (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run TEXT NOT NULL REFERENCES gin_run(ref),
    weighed TEXT NOT NULL,
    net_pounds INTEGER NOT NULL,
    ticket TEXT NOT NULL DEFAULT '',
    buyer TEXT NOT NULL DEFAULT ''
)
```

- `CREATE INDEX seed_load_by_run ON seed_load(run)`

- `CREATE UNIQUE INDEX seed_load_by_ticket ON seed_load(ticket) WHERE ticket <> ''`

### sqlite_sequence

```sql
CREATE TABLE sqlite_sequence (
    name,
    seq
)
```

### warehouse

```sql
CREATE TABLE warehouse (
    ref TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT NOT NULL DEFAULT '',
    location TEXT NOT NULL DEFAULT ''
)
```

### yard_hold

```sql
CREATE TABLE yard_hold (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module TEXT NOT NULL REFERENCES module(tag),
    reason TEXT NOT NULL,
    placed TEXT NOT NULL,
    placed_by TEXT NOT NULL DEFAULT '',
    lifted TEXT,
    lifted_by TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT ''
)
```

- `CREATE INDEX yard_hold_by_module ON yard_hold(module)`

- `CREATE UNIQUE INDEX yard_hold_one_active ON yard_hold(module) WHERE lifted IS NULL`

### yard_place

```sql
CREATE TABLE yard_place (
    module TEXT PRIMARY KEY REFERENCES module(tag),
    yard_row TEXT NOT NULL,
    position INTEGER NOT NULL,
    placed TEXT NOT NULL
)
```

- `CREATE UNIQUE INDEX yard_place_spot ON yard_place(yard_row, position)`
