# Data Histograms

`histogram.py` plots the value distributions of the join-key columns used by the two-relation [join experiments](../Join_Experiment/README.md). It makes one plot per column and skew level.

No histogram images are included in the repository.

## Prerequisites

- Generated `.tbl` files for each skew level, in the layout from the [data generation guide](../TPC-H_SkewData_Gen/README.md): `<DATA>/z0/`, `<DATA>/z1/`, `<DATA>/z1_5/`, with the orders table in `order.tbl`.
- Python 3 with `numpy`, `pandas`, and `matplotlib`. No versions are pinned or validated.
- Edit the hard-coded input path in the script. It currently reads:

  ```python
  file_path = '/data/leeyongh-psql/Data/TPC-H/' + z + '/' + table + '.tbl'
  ```

## Usage

```sh
cd Data_Histogram
python histogram.py
```

The script has no arguments. It writes `./z0/`, `./z1/`, and `./z1_5/`, relative to the current directory, and creates them if needed. Each file is named `<column>_<z>.png`, for example `z1_5/l_partkey_z1_5.png`. Existing images with the same name are overwritten.

## What is plotted

Ten columns (five join pairs) × three skew levels = 30 images:

| Join label | Columns (table, 0-based field index) |
|---|---|
| `Q9` | `ps_partkey` (partsupp, 0), `l_partkey` (lineitem, 1) |
| `Q10` | `c_custkey` (customer, 0), `o_custkey` (order, 1) |
| `Q11` (modified) | `o_orderdate` (order, 4), `l_shipdate` (lineitem, 10) |
| `Q12` | `o_orderkey` (order, 0), `l_orderkey` (lineitem, 0) |
| `Q15` | `s_suppkey` (supplier, 0), `l_suppkey` (lineitem, 2) |

For each image the script:

1. Reads the **entire** `.tbl` file with pandas (`delimiter='|'`, no header). For large scale factors `lineitem.tbl` may not fit in memory.
2. Keeps only the **first 200,000 rows** (`row_n`). For files that were not shuffled, these rows follow generation order and are not a random sample. See the [shuffle step](../TPC-H_SkewData_Gen/README.md#4-optional-shuffle-the-files).
3. Plots a histogram with `plt.hist`.

## Caveats

- **Numeric columns.** The sorted unique values are passed as `bins`. Matplotlib treats them as bin *edges*, not as one bar per value. N distinct values give N − 1 bins, and the last two values share the final bin. A column with only one distinct value in the sample does not give a usable histogram.
- **Date columns** (`o_orderdate`, `l_shipdate`). These are treated as strings, and `bins` is set to the number of distinct strings. How `plt.hist` handles string data depends on the matplotlib version. It may fail, or produce a categorical-looking plot whose bins do not match calendar dates.
- **Numeric detection.** Only the first value is checked to decide whether a column is numeric.
- **Trailing `|`.** If the files still end each row with `|`, pandas reads an extra empty column. The field indices above are unaffected.
