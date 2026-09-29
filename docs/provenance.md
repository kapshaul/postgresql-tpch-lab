# Source provenance and repository history

[Repository overview](../README.md) · [Generator guide](../TPC-H_SkewData_Gen/dbgen/README.md)

## External generator

The C generator is derived from [YSU-Data-Lab/TPC-H-Skew](https://github.com/YSU-Data-Lab/TPC-H-Skew), whose README calls it `tpch_skew_linux`. Its legacy documentation identifies the TPC-D population generator version 1.3.1 and the Transaction Processing Performance Council. The included [contributors file](../TPC-H_SkewData_Gen/dbgen/contributors.txt) names Feng George Yu. The original [Readme](../TPC-H_SkewData_Gen/dbgen/Readme), [History](../TPC-H_SkewData_Gen/dbgen/History), and [skew document](../TPC-H_SkewData_Gen/dbgen/README-SKEW.doc) are retained.

The original lab import did not record an upstream commit. For this reconstruction, the comparison base is [`2b9efffc7763c4b773875889139436a55b212a5e`](https://github.com/YSU-Data-Lab/TPC-H-Skew/commit/2b9efffc7763c4b773875889139436a55b212a5e), dated April 26, 2022, the latest upstream revision before the lab's 2024 history. This is an audited comparison base, not proof of the exact revision originally downloaded.

Comparing the lab snapshot before its documentation refresh with this revision:

- 44 files in the generator directory have corresponding upstream paths; 36 are byte-identical.
- Seven C/header files differ: `build.c`, `driver.c`, `dss.h`, `dsstypes.h`, `print.c`, `rnd.c`, and `rnd.h`.
- The remaining differing file is the lab's `README.md`.
- Twelve additional files are compiled executables or object files. Their build environment and correspondence to the checked-in sources were not recorded.

The source differences include independently generated line-item order keys, sequential order keys stored as `long`, associated output formatting, an additional RNG stream and seed, and multiplier initialization in `SkewIntCount`. These differences are grouped separately from the imported generator in the reconstructed history. They should not be attributed to the upstream project.

## Lab-specific work

The Python and shell tools provide PostgreSQL table loading and shuffling, prefix-latency measurements for selected joins, join-key histograms, and result-file maintenance. The loader paths, server settings, and measurement assumptions are documented in the component guides. This repository does not include the modified PostgreSQL server or archived timing results.

## History organization

The reconstructed history preserves the 19 upstream commits through the comparison base, including the original first commit, `Initial commit`. Subsequent commits separate vendoring the generator, local generator changes, data preparation and loading, join experiments, histograms, result maintenance, and the documentation refresh. The vendor step keeps the generator files used by this lab; unrelated upstream query templates and import helpers remain accessible in the upstream history.

These later commits organize the retained snapshot by responsibility. They are not a claim that the original development happened in that order. The previous 42-commit lab history was backed up before reconstruction. The repository's former name was `kapshaul/PSQL-tpch-lab`; its current name is `kapshaul/postgresql-tpch-lab`.
