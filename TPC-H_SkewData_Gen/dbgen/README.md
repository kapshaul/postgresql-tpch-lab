# Skew-Enabled `dbgen`

This directory contains the C source for a TPC-D/TPC-H-style population generator with Zipf skew support (`-z`), plus a local change to how `lineitem.l_orderkey` is generated. The lab uses it to create the flat files described in the [data generation guide](../README.md).

Use the output for research on skewed data only. It is **not** valid TPC-H benchmark data.

## Origin and attribution

- The base program is the **TPC-D Population Generator, version 1.3.1**, © Transaction Processing Performance Council 1994–1998 (see the source headers and `Readme`).
- The skew extensions (Zipf-distributed column values, `-z`) are credited in the source to **Surajit Chaudhuri and Vivek Narasayya (Jan '99)**. `README-SKEW.doc` describes them.
- The copy used here came from a Linux port of that skew generator. `contributors.txt` lists **Feng George Yu**. The matching repository is [YSU-Data-Lab/TPC-H-Skew](https://github.com/YSU-Data-Lab/TPC-H-Skew). The original import did not record a revision; the [provenance guide](../../docs/provenance.md) documents the audited comparison base.
- The original copyright notices and the legacy documents are kept as they are:

| File | Contents |
|---|---|
| `Readme` | Original DBGEN/QGEN manual (options, build, limitations) |
| `README-SKEW.doc` | Description of the skew extensions |
| `History`, `Bugs`, `Porting.Notes` | Original change history, known bugs, porting notes |
| `contributors.txt` | Contributor list of the Linux port |
| `dss.ddl`, `dss.ri`, `DistrTest.sql`, `verify.c`, `verify.rqd`, `10001001` | Original schema, constraints, and verification material (not used by this lab) |

## Local modification: lineitem orderkey

The previous README stated that "the distributed version of dbgen is not introducing skewness for the `orderkey` in the lineitem table" and that this version does. In the code, the change works as follows.

In `build.c` (`mk_order`), each lineitem row obtains its `l_orderkey` through a **separate skew stream** instead of copying its parent order key:

```c
RANDOM(o->l[lcnt].okey, L_OKEY_MIN, L_OKEY_MAX, L_OKEY_SD, skew, L_LINE_SIZE);
```

The value is drawn from the range `1 .. number of orders`, using its own random stream `L_OKEY_SD` (48), defined in `dss.h` and seeded in `rnd.h`. It is not copied from the parent order's `o_orderkey`. Consequences:

- Lineitem rows are no longer guaranteed to match the order they were generated with. Some orders may have no matching lineitems, and others may match many.
- Per-order line counts and associations with other columns change, including for `-z 0`. If order keys are unique and every lineitem key is in range, a full order–lineitem equijoin still returns one row per lineitem; the reassignment alone does not change that total cardinality.
- `o_totalprice` and `o_orderstatus` are still computed from the lines generated together with each order. They therefore do not correspond to the lineitem rows that share that `o_orderkey`.

Things to watch for in this copy:

- `dss.h` defines `MAX_STREAM` as `48`. `L_KEY_SD` is `49`, `rnd.h` initializes 50 seeds into arrays sized `MAX_STREAM + 1`, and `SkewIntCount()` indexes per-stream arrays with stream 49. This is an out-of-bounds access: an UndefinedBehaviorSanitizer run at SF 0.001, z 0 reported index 49 accesses in `rnd.c`, as well as a NaN-to-integer conversion. The normal build warned about excess seed initializers. Its effects on distributions and reproducibility are not validated.
- `build.c` declares `SkewIntCount(long, int, long)`, while `rnd.c` defines it with a `double` second argument. This incompatible declaration can pass the skew value incorrectly across compilation units.
- When `mk_order` uses the skewed line count, it passes `L_KEY_SD` to `SkewIntCount()`. That function treats `-z` values above `4` as uniform, while `SkewInt()` accepts up to `5` (a per-column random mix).

## Building

The makefiles in this directory are 1990s-era variants of `makefile.suite`:

| Makefile | `DATABASE` / `PLATFORM` / other |
|---|---|
| `makefile_linux.original` | `SQLSERVER` / `SUN` |
| `makefile_ubuntu` | `SQLSERVER` / `LINUX` |
| `makefile_centos` | `MYSQL` / `CENTOS`, `WORKLOAD=TPCH` |
| `makefile_MacSolaris` | `MYSQL` / `MACOSX`, `WORKLOAD=TPCH` |
| `makefile.squall` | `SQLSERVER` / `LINUX`, adds `-I/usr/include/sys` |
| `makefile.suite` | Original TPC template (`DATABASE` and `PLATFORM` left empty) |

The original command `make -f makefile_linux.original` fails because the rule `$(OBJ1): config.h makefile` refers to a missing file named `makefile`. Copying a selected variant to that name resolves this prerequisite. On Apple Clang 21, the default macOS build then fails on implicit function declarations.

The following **diagnostic build** succeeded in an isolated copy on macOS. Run it from the repository root; all generated files stay under the temporary directory. It builds only `dbgen`, not `qgen`:

```sh
tpch_build_dir=$(mktemp -d)
cp -R TPC-H_SkewData_Gen/dbgen "$tpch_build_dir/dbgen"
(
  cd "$tpch_build_dir/dbgen" || exit 1
  cp makefile_MacSolaris makefile
  make clean
  make dbgen CFLAGS='-O -std=gnu89 -fcommon -Wno-implicit-function-declaration -Wno-int-conversion -DMYSQL -DMACOSX -DTPCH'
  ./dbgen -s 0.001 -z 0
)
```

The compatibility flags allow old C constructs and shared global definitions; they do not repair the source defects above. Separate small runs with `-z 0`, `-z 1`, and `-z 1.5` exited successfully and each produced eight files, including 1,500 orders and 6,000 lineitems. A subsequent build with `-fsanitize=address,undefined` in both compiler and linker flags reported the out-of-bounds accesses. **Successful file generation is therefore not a correctness or benchmark-validation result.** Repair and revalidate the generator before using the output for measurements.

`make clean` removes executables and `.o` files, so keep builds in a disposable copy. `dbgen` needs `dists.dss` at run time. `./dbgen -h` prints help but exits with status 1 in the tested build.

### Archived binaries

`dbgen`, `qgen`, `dbgen.original`, `qgen.original`, the `*.o` files, and the Visual C++ project files (`dbgen.dsp`, `.dsw`, `.ncb`, `.opt`, `.plg`) are committed build artifacts from earlier environments. They are kept for reference only. They are not portable builds, and it has not been confirmed that they match the current source. Rebuild from source instead of running them.

## Usage

Run `dbgen` from this directory, or set `DSS_CONFIG` to the directory that holds `dists.dss`. Output goes to the current directory, or to `DSS_PATH` if that is set; see `Readme`. Existing files are not overwritten unless you pass `-f`.

```sh
./dbgen -vf -s 1 -z 1.5     # SF 1 with requested skew 1.5; run only after reviewing the defects above
./dbgen -vf -s 0.1          # small uniform dataset
```

- `-s <n>`: scale factor. SF 1 is nominally about 1 GB in standard dbgen. Sizes with skew enabled have not been measured.
- `-z <n>`: Zipf skew, parsed with `atof` (for example `0`, `1`, `1.5`). `0` means uniform. Values from `0` to `4` are used as the Zipf exponent, `5` (or `-1`) picks a random exponent from 0 to 4 for each column, and values outside the range fall back to uniform. This describes the parser and `SkewInt` branches, not a verified distributional guarantee in the presence of the defects above. The lab uses `0`, `1`, and `1.5`, and stores them in directories `z0`, `z1`, and `z1_5`.
- The orders file is named `order.tbl` (singular). Every row ends with a trailing `|`, which must be removed before loading into PostgreSQL. See the [data generation guide](../README.md#3-remove-the-trailing-).

### Help output

Output of `./dbgen -h` from an earlier build (kept from the previous README):

```
./dbgen -h
TPC-D Population Generator (Version 1.3.1)
Copyright Transaction Processing Performance Council 1994 - 1998
USAGE:
dbgen [-{vfFD}] [-O {fhmst}][-T {pcsoPSOL}]
	[-s <scale>][-C <procs>][-S <step>]
dbgen [-v] [-O {dhmrt}] [-s <scale>] [-U <updates>] [-r <percent>]

-C <n> -- use <n> processes to generate data
          [Under DOS, must be used with -S]
-D     -- do database load in line
-f     -- force. Overwrite existing files
-F     -- generate flat files output
-h     -- display this message
-n <s> -- inline load into database <s>
-O d   -- generate SQL syntax for deletes
-O f   -- over-ride default output file names
-O h   -- output files with headers
-O m   -- produce columnar output
-O r   -- generate key ranges for deletes.
-O s   -- generate seed sets ONLY
-O t   -- use TIME table and julian dates
-r <n> -- updates refresh (n/100)% of the
          data set
-R <n> -- resume seed rfile generation with step <n>
-s <n> -- set Scale Factor (SF) to  <n>
-S <n> -- build the <n>th step of the data set
-T c   -- generate cutomers ONLY
-T l   -- generate nation/region ONLY
-T L   -- generate lineitem ONLY
-T n   -- generate nation ONLY
-T o   -- generate orders/lineitem ONLY
-T O   -- generate orders ONLY
-T p   -- generate parts/partsupp ONLY
-T P   -- generate parts ONLY
-T r   -- generate region ONLY
-T s   -- generate suppliers ONLY
-T S   -- generate partsupp ONLY
-U <s> -- generate <s> update sets
-v     -- enable VERBOSE mode
-z     -- **generate skewed data distributions**

To generate the SF=1 (1GB) database population , use:
	dbgen -vfF -s 1

To generate the qualification database population (100 MB), use:

	dbgen -vfF -s 0.1

To generate updates for a SF=1 (1GB), use:
	dbgen -v -O s -s 1
	dbgen -v -U 1 -s 1
```

`qgen` generates TPC-D query text from templates. This lab does not use it.
