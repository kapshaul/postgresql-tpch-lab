# Data Generation and Loading

This directory produces the skewed tables that the [join experiments](../Join_Experiment/README.md) use:

1. Build the modified `dbgen` and generate flat files (`*.tbl`) for each skew value.
2. Remove the trailing `|` from every row.
3. Optionally shuffle the rows of each file.
4. Load everything into PostgreSQL with `script_full_load_custom.py`.

All paths and connection settings in these scripts are hard-coded for the original lab machine. Edit them before running anything.

## Files

| File | Purpose |
|---|---|
| [`dbgen/`](dbgen/) | Skew-enabled data generator (C source, legacy docs, archived binaries). See the [dbgen guide](dbgen/README.md). |
| `remover.sh` | Strips the trailing `\|` from the eight `.tbl` files in **one** hard-coded directory. |
| `shuffle_tables.sh` | Shuffles six `.tbl` files per skew directory **in place** with `shuf`. |
| `script_full_load_custom.py` | The loader that matches the join experiments: 6 tables × 3 skew values × 3 shuffles. |
| `script_full_load.py` | An older loader for a different directory layout and table naming. It does not match the join experiments. |

## 1. Build `dbgen`

Building is described in the [dbgen guide](dbgen/README.md#building). Note that the build command from earlier versions of this README, `make -f makefile_linux.original`, fails in a fresh copy: the makefiles list a file named `makefile` as a prerequisite, and that file is not checked in.

## 2. Generate one dataset per skew value

By default, `dbgen` reads `dists.dss` from its working directory; `DSS_CONFIG` can point to another directory. It writes `customer.tbl`, `lineitem.tbl`, `nation.tbl`, `order.tbl` (singular), `part.tbl`, `partsupp.tbl`, `region.tbl`, and `supplier.tbl` into the current directory.

The experiments use three skew values. `-z` takes a number, while directory and table names use `1_5` in place of `1.5`:

| Skew (`-z`) | Data directory | Table-name suffix |
|---|---|---|
| `0` (uniform) | `z0/` | `0` |
| `1` | `z1/` | `1` |
| `1.5` | `z1_5/` | `1_5` |

Example for one skew value. It assumes a working `dbgen` build and that `DATA_ROOT` is where you keep the data. The SF 1 command below has not been rerun. The [generator guide](dbgen/README.md#building) records a much smaller diagnostic run and the correctness defects that still need repair:

```sh
: "${DATA_ROOT:?Set DATA_ROOT to the intended data directory}"
cd TPC-H_SkewData_Gen/dbgen
./dbgen -vf -s 1 -z 1.5          # -f overwrites existing *.tbl files in this directory
mkdir -p "$DATA_ROOT/z1_5"
mv *.tbl "$DATA_ROOT/z1_5/"
```

Repeat with `-z 0` → `z0/` and `-z 1` → `z1/`. Use the same `-s` for all three.

- `-s` is the TPC scale factor. In standard dbgen, SF 1 is roughly 1 GB of flat files. With skew enabled the actual file sizes can differ, and this repository has no measured sizes for any scale factor.
- `./dbgen -h` lists the other options.

## 3. Remove the trailing `|`

Every row ends with a `|` delimiter. With `DELIMITER '|'`, PostgreSQL `COPY` treats that as an extra, empty column and rejects the row, so the trailing `|` must be removed before loading.

Inside one data directory, with GNU `sed`:

```sh
sed -i 's/|$//' *.tbl            # edits files in place
```

On macOS/BSD `sed`, use `sed -i '' 's/|$//' *.tbl`.

`remover.sh` does the same thing for the eight standard table files, but only in the single directory hard-coded in `path=` (currently `/data/leeyongh-psql/Data/TPC-H/z1_5`). To use it, edit `path` and run it once per skew directory. Earlier documentation called this script `remove.sh`.

Check the result with `head -n 3 customer.tbl`. Rows should no longer end with `|`.

## 4. (Optional) Shuffle the files

The files follow generation order; this does not imply that every join-key column is sorted. `shuffle_tables.sh` rewrites `customer`, `lineitem`, `order`, `part`, `partsupp`, and `supplier` under `$directory/{z0,z1,z1_5}/` in random order. It uses GNU `shuf`, which base macOS does not provide.

- The script **overwrites the original files** (`shuf file -o file`).
- It uses a different hard-coded base directory (`/data/leeyongh-psql/Data/TPC-H-Skew/test`) from the loader and the histogram script (`/data/leeyongh-psql/Data/TPC-H`). Point `directory` at your data before running it.
- No random seed is set, so the order cannot be reproduced.

This step is not required for the join experiments. The loader already inserts every table in random order (see below). File order does matter for the [histograms](../Data_Histogram/README.md), which plot only the first 200,000 rows of each file.

## 5. Load into PostgreSQL

`script_full_load_custom.py` takes no arguments. Before running it:

- Edit the connection in `main()`. It currently uses `host="/tmp/"`, `database="leeyongh"`, `user="leeyongh"`, and `port="5245"`.
- Edit the path in `makeCopyString()`. It currently reads `/data/leeyongh-psql/Data/TPC-H/z<z>/<table>.tbl`.
- The loader uses **server-side** `COPY ... FROM '<path>'`. The files must be readable by the PostgreSQL server process on the server host, and the role needs superuser rights or `pg_read_server_files`, plus the required table/schema privileges. See [COPY](https://www.postgresql.org/docs/current/sql-copy.html).
- Make sure there is enough disk space for three copies of every table plus one staging copy for each skew value.

Then run:

```sh
python TPC-H_SkewData_Gen/script_full_load_custom.py
```

### What the loader does

For each skew value `z` in `0`, `1`, `1_5`:

1. It **drops** and recreates the staging tables `part_temp<z>`, `supplier_temp<z>`, `lineitem_temp<z>`, `order_temp<z>`, `customer_temp<z>`, and `partsupp_temp<z>`. These are regular tables, not `TEMPORARY` ones. It then `COPY`s the matching `.tbl` file into each.
2. For each shuffle `s` in `1`, `2`, `3`, it **drops** and recreates `<table>1<s><z>` and fills it with `INSERT ... SELECT * FROM <table>_temp<z> ORDER BY random()`, then commits.
3. It drops the staging tables.

The result is 54 tables named `<table>1<shuffle><z>`, for example `part110`, `order121`, and `lineitem131_5`. Identifiers are unquoted, so PostgreSQL stores them in lower case. `nation` and `region` are not loaded.

Things to know:

- **Destructive:** existing tables with these names are dropped without confirmation.
- **Not atomic:** work is committed after each shuffle. If the script fails partway through, some tables are rebuilt, others are not, and staging tables may be left behind.
- The final staging-table drops for `z = 1_5` are not followed by a commit before the script exits, so disconnecting rolls back those drops and can leave the `*_temp1_5` tables behind. See [psycopg transaction handling](https://www.psycopg.org/docs/connection.html#connection.close). Check for them and drop them manually if needed.
- No indexes, keys, or constraints other than `NOT NULL` are created, and `ANALYZE` is not run. The planner relies on autovacuum statistics, if any.
- `random()` is not seeded, so each run produces a different physical row order.

### Legacy loader

`script_full_load.py` is kept for reference only. It loads pre-shuffled files from another user's directory (`/data/bakhtiyar-psql/...`) into tables with prefix `2` and shuffles `1`, `3`, `4` (for example `lineitem211_5`). The join experiment script expects prefix `1` and shuffles `1`–`3`, so this loader's tables will not be found.
