# PostgreSQL TPC-H Lab

Research scripts for studying how **data skew** affects the **time to first results** of join queries in PostgreSQL.

The lab has three stages:

1. **Generate and load data.** Build skewed, TPC-H-derived tables with a modified `dbgen`, clean the flat files, and load several randomly ordered copies into PostgreSQL.
2. **Run join experiments.** Stream the result of selected two- and three-relation joins through a server-side cursor and record how long the client waits to receive the first *K* rows.
3. **Plot histograms.** Draw the distributions of the join-key columns for each skew level.

Repository: <https://github.com/kapshaul/postgresql-tpch-lab> · [Source provenance and history](docs/provenance.md)

## What this repository is (and is not)

- It **is** a set of research scripts. They were written for one lab environment and contain hard-coded paths, database names, and ports that you must edit.
- It is **not** an implementation or an audited run of the TPC-H benchmark. The data comes from a *modified* TPC-D/TPC-H-style generator, and the join queries are simplified joins labeled after TPC-H queries. They are not the standard TPC-H query texts.
- It does **not** include generated datasets, experiment results, plots, the PostgreSQL server build used in the original experiments, or a pinned software environment.

## Repository layout

| Path | Contents | Guide |
|---|---|---|
| [`TPC-H_SkewData_Gen/`](TPC-H_SkewData_Gen/) | Data preparation scripts and the PostgreSQL loader | [Data generation and loading](TPC-H_SkewData_Gen/README.md) |
| [`TPC-H_SkewData_Gen/dbgen/`](TPC-H_SkewData_Gen/dbgen/) | Skew-enabled `dbgen` C source, legacy docs, and archived binaries | [dbgen guide](TPC-H_SkewData_Gen/dbgen/README.md) |
| [`Join_Experiment/`](Join_Experiment/) | Join timing script, batch runner, and result-maintenance utilities | [Join experiment guide](Join_Experiment/README.md) |
| [`Data_Histogram/`](Data_Histogram/) | Histogram plotting script for join-key columns | [Histogram guide](Data_Histogram/README.md) |

## Workflow at a glance

```text
dbgen -z {0, 1, 1.5}  ──►  z0/ z1/ z1_5/ *.tbl  ──►  strip trailing '|'  ──►  script_full_load_custom.py
                                   │                                              │
                                   ▼                                              ▼
                             histogram.py                      54 tables: <table>1<shuffle><z>
                                                                                 │
                                                                                 ▼
                                                                    script_experiment.py
```

1. **Data generation and loading:** [`TPC-H_SkewData_Gen/README.md`](TPC-H_SkewData_Gen/README.md)
   - Build `dbgen` and generate one dataset for each Zipf skew value: `0`, `1`, and `1.5`. Directories and table names use `1_5` for `1.5`.
   - Remove the trailing `|` from every row so that PostgreSQL `COPY` accepts the files.
   - Run `script_full_load_custom.py`. It loads six tables (`part`, `supplier`, `partsupp`, `customer`, `order`, `lineitem`) for each skew value and makes three randomly ordered copies of each. The result is 6 × 3 × 3 = 54 tables with names such as `lineitem111_5` (table `lineitem`, prefix `1`, shuffle `1`, z `1_5`).
2. **Join experiments:** [`Join_Experiment/README.md`](Join_Experiment/README.md)
   - Run `python script_experiment.py OUTPUT_PREFIX Z_VALUE QUERY`, for example `... Results/2R/Q9/0 0 Q9`.
   - For each skew value, the script runs the chosen join against all three shuffled copies. It then writes a log, a summary, and two `.dat` files that map *K* (rows received) to elapsed time.
3. **Histograms:** [`Data_Histogram/README.md`](Data_Histogram/README.md)
   - Run `python histogram.py` to plot the first 200,000 rows of each of the ten join-key columns for `z0`, `z1`, and `z1_5`. It is configured to produce 30 PNG files; the plotting caveats in the guide can prevent completion.

## Requirements

- A C compiler and `make` to build `dbgen`. The makefiles date from the 1990s. See the [dbgen guide](TPC-H_SkewData_Gen/dbgen/README.md) for known build issues.
- A PostgreSQL server that you can connect to and that can read the generated `.tbl` files through server-side `COPY`. The database role needs table-creation privileges and the server-file privileges described in the [PostgreSQL COPY documentation](https://www.postgresql.org/docs/current/sql-copy.html).
- Python 3 with `psycopg2` for loading and experiments, and `numpy`, `pandas`, and `matplotlib` for histograms. No versions are pinned or validated.
- GNU `sed` and GNU `shuf` for the optional shell helpers. On macOS, the base `sed -i` syntax is different and `shuf` is not installed.

## Before you run anything

The scripts were not written as a portable tool. Expect to make these changes first:

- **Paths.** Update the absolute paths in `remover.sh`, `shuffle_tables.sh`, `script_full_load_custom.py`, `experiment.sh`, and `histogram.py`. They currently point at `/data/leeyongh-psql/...`.
- **Generator correctness.** A diagnostic build can produce small files, but sanitizer checks found out-of-bounds RNG-array accesses, and a function prototype disagrees with its definition. Resolve the [generator defects](TPC-H_SkewData_Gen/dbgen/README.md#local-modification-lineitem-orderkey) before treating its output as validated experimental data.
- **Connection settings.** The loader and join script connect to database/user `leeyongh` through the Unix socket in `/tmp/` on port `5245`. These values are hard-coded constants. There are no command-line flags or environment variables for them.
- **Custom planner settings.** `script_experiment.py` sets `enable_block`, `enable_fastjoin`, and `enable_fliporder`. These parameters come from a modified PostgreSQL server that is not included here. Stock PostgreSQL rejects them, so the script needs those lines removed before it can run. See the [join guide](Join_Experiment/README.md#required-changes-before-running).
- **Destructive operations.** The loader drops and recreates its tables. `shuffle_tables.sh` and `remover.sh` overwrite files in place. The helpers in `Join_Experiment/delete.py` and `Join_Experiment/etc/` delete or overwrite result files. Read each guide before running anything.

## Interpreting results

- The join script measures **client-observed** latency. This is wall-clock time in Python while rows arrive in batches of 100 through a server-side cursor, so it includes network and driver overhead. It is not server execution time.
- The queries have `LIMIT` but no `ORDER BY`. Which rows arrive first therefore depends on the plan and the physical row order.
- The three "shuffles" are differently ordered copies of the **same** generated data. They are not independent samples.
- The modified generator assigns `lineitem.l_orderkey` through a separate skew stream instead of copying the parent order key. This changes per-order line counts and relationships to other columns; it does not by itself imply a different total size for a full order–lineitem equijoin. See the [dbgen guide](TPC-H_SkewData_Gen/dbgen/README.md#local-modification-lineitem-orderkey).

## Attribution

The data generator is based on the TPC-D Population Generator (version 1.3.1), © Transaction Processing Performance Council, with skew extensions by Surajit Chaudhuri and Vivek Narasayya (noted in the source headers). The matching external code is [YSU-Data-Lab/TPC-H-Skew](https://github.com/YSU-Data-Lab/TPC-H-Skew); the [provenance guide](docs/provenance.md) records the comparison revision and local changes. The original copyright notices and legacy documentation are kept unchanged in [`TPC-H_SkewData_Gen/dbgen/`](TPC-H_SkewData_Gen/dbgen/).
