# Join Experiment

`script_experiment.py` runs one labeled join against the three shuffled copies of the tables for a chosen skew value. It streams the result through a PostgreSQL server-side cursor and records how long the client has waited by the time it has received *K* rows, for increasing *K*. `experiment.sh` is a batch wrapper that runs several queries and skew values.

The tables must first be created with the [loader](../TPC-H_SkewData_Gen/README.md#5-load-into-postgresql).

## Files

| File | Purpose |
|---|---|
| `script_experiment.py` | Runs one query label for one skew value and writes `.log`, `.txt`, and `.dat` outputs |
| `experiment.sh` | Loops over queries `Q9 Q10 Q11 Q15` × z `0 1 1_5` and calls the script above |
| `delete.py` | Maintenance: **deletes** every non-`.dat` file under `./data/` |
| `etc/directories.py` | Maintenance: **recursively deletes** subdirectories under `./data/workmem_500MB/2R/<Q>/` that are not in an allow-list |
| `etc/convert.py` | Maintenance: filters `.dat` files under `data/data/...` to selected *K* values and **overwrites** them |

The maintenance scripts operate on result layouts from the original lab, not on anything the main script creates by default. They are not part of the normal workflow.

## Prerequisites

- A PostgreSQL server that holds the 54 tables `<table>1<shuffle><z>` created by `script_full_load_custom.py`. Each run reads the three shuffles `1`, `2`, `3` for one `z`.
- Python 3 with `psycopg2`.
- The parent directory of `OUTPUT_PREFIX` must already exist. The script does not create it.

## Required changes before running

The script has no command-line flags or environment variables for configuration. Edit the constants at the top of `script_experiment.py`:

| Constant | Current value | Meaning |
|---|---|---|
| `DATABASE`, `USER` | `leeyongh` | Database and role |
| `HOST` | `/tmp/` | Unix-socket directory (or a hostname) |
| `PORT` | `5245` | Server port |

The `settings` list also includes three parameters that **do not exist in stock PostgreSQL**:

```python
'set enable_block = OFF;',
'set enable_fastjoin = OFF;',
'set enable_fliporder = OFF;',
```

They belong to a modified PostgreSQL server used in the original research, and that server is not part of this repository. On stock PostgreSQL the first of these `SET`s fails with *unrecognized configuration parameter*. The script catches the error, retries, and eventually stops without writing the `.dat` files. Remove or comment out these three lines unless you are running the matching patched server.

`experiment.sh` also needs editing. It calls `python /data/leeyongh-psql/Experiment/script_experiment.py` with an absolute path, and it writes under `./Results/test/testing/...`.

## Usage

The script takes exactly **three** positional arguments. Its usage message says "two", but three are required.

```sh
python script_experiment.py OUTPUT_PREFIX Z_VALUE QUERY
```

| Argument | Values | Meaning |
|---|---|---|
| `OUTPUT_PREFIX` | path without extension | Base name for the output files |
| `Z_VALUE` | `0`, `1`, `1_5` | Table-name suffix (skew level) |
| `QUERY` | a label from the table below | Which join to run. An unknown label makes the script exit with status 1. |

Example, after the changes above and with the tables loaded:

```sh
cd Join_Experiment
mkdir -p Results/2R/Q9
python script_experiment.py Results/2R/Q9/0 0 Q9
```

This writes `Results/2R/Q9/0.log`, `0.txt`, `0.dat`, and `0_weight.dat`.

To run the batch wrapper after fixing its Python path:

```sh
cd Join_Experiment
bash experiment.sh
```

It writes to `./Results/test/testing/{2R|3R}/<query>/{0|1|15}`. Note that `1_5` becomes `15` in the output filename prefix, and `Q9_3R` is stored under `3R/Q9`.

## Queries

Each label runs `SELECT * FROM ... WHERE ... LIMIT n` against `<table>1<s><z>` for `s` = `1`, `2`, `3`. The labels refer to the TPC-H query that the join pair was taken from. They are **not** the standard TPC-H queries: there are no filters, aggregates, or `ORDER BY`. (The `order` tables hold TPC-H `orders` data.)

| Label | Relations | Join predicate(s) | `LIMIT` |
|---|---|---|---|
| `Q9` | partsupp, lineitem | `ps_partkey = l_partkey` | 240,000 |
| `Q10` | customer, order | `c_custkey = o_custkey` | 15,000 |
| `Q11` | order, lineitem | `o_orderdate = l_shipdate` (modified; not a key join) | 13,000,000 |
| `Q12` | order, lineitem | `o_orderkey = l_orderkey` | 60,000 |
| `Q15` | supplier, lineitem | `s_suppkey = l_suppkey` | 60,000 |
| `Q2` | part, supplier, partsupp | `p_partkey = ps_partkey AND s_suppkey = ps_suppkey` | 8,000 |
| `Q3` | customer, order, lineitem | `c_custkey = o_custkey AND o_orderkey = l_orderkey` | 60,000 |
| `Q5` | order, supplier, lineitem | `s_suppkey = l_suppkey AND o_orderkey = l_orderkey` | 60,000 |
| `Q8` | part, supplier, lineitem | `p_partkey = l_partkey AND s_suppkey = l_suppkey` | 60,000 |
| `Q9_3R` | supplier, partsupp, lineitem | `s_suppkey = l_suppkey AND ps_suppkey = l_suppkey` | 4,800,000 |
| `test` | part, supplier, lineitem | Same join as `Q8`, predicates reordered | 60,000 |

Notes:

- Because there is no `ORDER BY`, *which* rows arrive first depends on the plan and on the physical order of each shuffled copy.
- Joins on `o_orderkey = l_orderkey` (`Q12`, `Q3`, `Q5`) are affected by the generator's independent `l_orderkey` draw. See the [dbgen guide](../TPC-H_SkewData_Gen/dbgen/README.md#local-modification-lineitem-orderkey).
- The three shuffles are reordered copies of the same generated data, not independently generated datasets.

## Session settings

Before running the queries, the script applies these settings in the same session: `enable_material = OFF`, `max_parallel_workers_per_gather = 0`, `enable_seqscan = ON`, index, index-only, and bitmap scans `OFF`, `enable_nestloop = ON`, `enable_hashjoin = OFF`, `enable_mergejoin = OFF`, `work_mem = 64MB`, and `statement_timeout = 1800000` (30 min).

These switches influence planner choices; some methods, including nested loops, cannot be eliminated completely by disabling their switch. See the [PostgreSQL planner documentation](https://www.postgresql.org/docs/current/runtime-config-query.html). The script never runs `EXPLAIN`, so the plan that actually ran is not recorded. Check it yourself if it matters.

## What is measured

For each query on each shuffle, the script:

1. Opens a named (server-side) cursor with `itersize = 100`. psycopg2 therefore fetches rows from the server in batches of 100.
2. Calls `execute()` and writes the time taken to the log as "Time before executing". This time is **not** included in the measurements below.
3. Starts the clock and iterates over the rows. For row *j* = 1, 2, …, with Δt<sub>j</sub> being the time since the previous row (or since the start):
   - **unweighted time** = wall-clock time since the start of iteration
   - **weighted time** = Σ<sub>j</sub> σ<sup>j</sup> · Δt<sub>j</sub>, with σ = `SIGMA` = 0.99

These are client-side Python `time()` measurements. They include network round trips, driver and Python overhead, and the time the server spends producing each batch. They are **not** server execution times. Rows inside a batch arrive almost instantly, so the time is concentrated at batch boundaries. The weight σ<sup>j</sup> decays quickly (0.99<sup>100</sup> ≈ 0.37, 0.99<sup>1000</sup> ≈ 4×10⁻⁵), so later intervals receive much smaller weights. Their actual contribution still depends on how long those intervals are.

### Sampling points and stopping

- Checkpoints are `int(100 × 1.5^i)` for i = 0, 1, … (100, 150, 225, 337, 506, …). The row count is compared with the next checkpoint only when it is a multiple of 100, so the recorded *K* is the first multiple of 100 at or after each checkpoint. At most one checkpoint is recorded per check.
- Iteration stops after 100 recorded points (`DATA_LIMIT`), when `TIME_LIMIT` = 180 s has passed, or when the query returns no more rows. The time limit is checked only at multiples of 100 rows, so a slow batch can run past it. The server-side `statement_timeout` of 30 minutes applies to individual statements; it is not a hard deadline for the entire Python run.
- Rows after the last multiple of 100 are counted in "Total joined tuples fetched", but their elapsed time is not included in the reported checkpoint measurements. The reported "Time of current query run" is the time at the last multiple of 100, or 0 if fewer than 100 rows were returned.

### Repetition and aggregation

- `TEST_NUMBER = 1`: each query runs once per shuffle, and its points are written to the `.txt` summary.
- Results from the three shuffles are merged by *K*. The first shuffle's points are taken as they are. Later shuffles are intersected on common *K* values, provided the number of distinct *K* values differs by at most 2. If it differs by more, the whole run restarts on a new connection, up to `MAX_GLOBAL_RETRIES = 3` attempts. On the last attempt, results are merged with a **union** instead.
- For the final averages, a *K* is written only if at least two shuffles contributed to it. Output stops at the first *K* that fails this test. The average is a plain mean. No variance or confidence interval is computed.

## Output files

For `OUTPUT_PREFIX = P`:

| File | Mode | Contents |
|---|---|---|
| `P.log` | appended | Timestamp, query text, per-checkpoint `K, unweighted, weighted`, total rows fetched, run time |
| `P.txt` | overwritten per invocation | Per-query points, then "Average Execution Times Across Queries". Output from failed attempts that were later retried stays in this file. |
| `P.dat` | overwritten | `K<TAB> average unweighted seconds` |
| `P_weight.dat` | overwritten | `K<TAB> average weighted seconds` |

No example results are included in the repository.

## Known limitations

- If the very first connection attempt fails, the `finally` blocks refer to `conn` before it has been assigned. The script then ends with a `NameError` traceback that hides the original error.
- If later attempts fail, the errors are only printed. The script still prints "The test is finished." and exits with status 0, possibly without `.dat` files. Check the outputs, not the exit status.
- "Max global retries reached" is printed whenever the third attempt was used, even if that attempt succeeded.
- There is no warm-up or cache control between runs, and no random seed, so results depend on the server's cache state and on the shuffle order produced by the loader.
