# Benchmarks

Use `python -m benchmarks` to choose a suite. All suites exclude setup and
warmups, retain wall/CPU samples, validate every output outside timing, and
record versions, thread counts, source revision and actual plugin binary hashes.
Each run requires a new JSON output path. Existing evidence is never overwritten.

The [2026-11-25 report](results/2026-11-25-large-data.md) contains measured
before/after timings, limitations and a downloadable raw-results archive.
Those are historical measurements; small smoke runs below only verify the harness.

## Start here

```bash
make sync-bench
make bench BENCH_OUTPUT=/tmp/h3-duckdb.json
```

`make bench` builds the release extension and runs the DuckDB suite. `make
bench-h2h` remains an alias for the same workflow. Both accept `BENCH_ARGS` and
`BENCH_OUTPUT`; the default is five million scalar rows, 250,000 list rows,
2,000 polygons, and eight threads. Install DuckDB H3 once, if needed, by adding
`--install-extension` to `BENCH_ARGS`. Installation never happens implicitly.

For a quick check of all DuckDB workloads:

```bash
make bench BENCH_OUTPUT=/tmp/h3-smoke.json \
  BENCH_ARGS='--threads 2 --rows 128 --list-rows 32 --polygon-rows 2 --warmups 1 --iterations 2'
```

After building with `make install-release`, use `UV_NO_SYNC=1` to prevent uv
from replacing the release extension during a measurement. Run benchmarks
sequentially with no competing builds or heavy processes. Development builds
are not representative.

```bash
UV_NO_SYNC=1 uv run -m benchmarks --help
UV_NO_SYNC=1 uv run -m benchmarks duckdb --list
UV_NO_SYNC=1 uv run -m benchmarks internal --list
UV_NO_SYNC=1 uv run -m benchmarks python --help
```

## Choose the comparison

| Suite | Purpose | Coverage and validation |
| --- | --- | --- |
| `duckdb` | Matched Polars/DuckDB H3 performance, optionally with a saved Polars baseline | 33 workloads including two identity controls; all values checked after every output, with documented type/order/float normalization |
| `internal` | Broad Polars performance and exact before/after regression checks | 53 workloads; exact values, dtypes and list order against a saved baseline; without a baseline, checks repeatability only |
| `python` | Polars expressions versus Python H3 callbacks in a Polars workflow | 14 operations, including numeric boundaries and paths; same input/output representation, every output validated |
| `baselines` | Optional plain Python H3 and h3pandas comparisons with hard subprocess deadlines | Six matched string-ID workloads; every output validated, timeouts/skips publish no partial timings |
| `compare` | Summarize matched saved measurements | Refuses incomplete runs and incompatible settings/environments; reports each operation/mode separately |

All runners accept `--functions`, `--rows`, `--threads`, `--iterations`,
`--warmups`, `--plugin-path`, `--output` and `--list`. Thread limits are applied
before engine imports. The default is five measured samples after two excluded
warmups. Engine order alternates for two engines; three-engine runs rotate and
reverse order. JSON records medians, min/max, individual wall/CPU samples and
output chunk counts. Runs checkpoint after each completed case; `status` is
`running`, `failed`, `partial`, or `complete`, so incomplete results are explicit.
The optional `baselines` suite uses one warmup and three samples by default.

### DuckDB and saved baselines

```bash
UV_NO_SYNC=1 uv run --group benchmarking -m benchmarks duckdb \
  --threads 8 --rows 5000000 --list-rows 250000 --polygon-rows 2000 \
  --baseline-plugin /absolute/path/to/original.abi3.so \
  --plugin-path /absolute/path/to/current.abi3.so \
  --output /tmp/h3-paired.json

UV_NO_SYNC=1 uv run -m benchmarks compare \
  /tmp/h3-paired.json /tmp/h3-paired.json --baseline-engine baseline
```

The saved binaries run on identical inputs within one process. Keep the original
release binary before rebuilding; plugin hashes identify what actually ran even
in a dirty development checkout. A baseline is optional for DuckDB comparisons.

| Mode | Timed work |
| --- | --- |
| `resident` | Preloaded inputs; Polars DataFrame creation versus DuckDB temporary-table materialization. Includes allocation/storage, excludes output export. |
| `arrow-materialized` | Query plus Arrow output. DuckDB first materializes a native result table, then exports it; both steps are timed. |
| `arrow-output` | Preloaded native inputs; full query execution and direct Arrow output. |
| `arrow-scan` | Polars native input versus DuckDB registered Arrow batches, both producing Arrow output. Measures an interchange scenario. |

The first two run by default. Select all four with `--modes resident
arrow-materialized arrow-output arrow-scan`. Input creation, Arrow conversion and
native DuckDB ingestion are recorded separately. Arrow input is batched (default
65,536 rows) so a single huge chunk does not restrict DuckDB parallelism.

Direct DuckDB SELECT/Arrow fetching can use much less CPU parallelism than
native materialization. Compare CPU/wall ratios before attributing a gap to
copying. No mode measures pure H3 kernel time. Identity projections expose
representation costs and are excluded from H3 speedup claims; never subtract
their noisy timings from operation times.

Use `--layout chunked` or `--layout sliced` to exercise Arrow layouts and
`--null-every 7` for nullable inputs. Cross-library null conventions differ for
some operations: those cases fail validation rather than silently normalizing
away a behavioral difference.

The deterministic corpus covers valid Ohio cells, strings, nearby-cell
relationships, list expansion, WKB polygons and a composed indexing/parent
pipeline. Integer widths are normalized; unordered cell lists are sorted outside
timing. Floating values use relative tolerance 1e-7 and absolute tolerance 1e-9.
Numeric boundaries are not compared with DuckDB's WKT formatting. Pentagon,
invalid-value and global edge cases belong to the correctness suite; these
benchmarks do not claim exhaustive geographic coverage.

### Broad internal checks

```bash
UV_NO_SYNC=1 uv run -m benchmarks internal \
  --baseline-plugin /absolute/path/to/original.abi3.so \
  --plugin-path /absolute/path/to/current.abi3.so \
  --rows 100000 --threads 8 --output /tmp/h3-regression.json
```

All 46 historical internal cases are retained, alongside five string-list cases
for children, traversal, and compaction, and two compaction workloads with large
sets in a small number of rows. Coverage includes local IJ, compaction,
metrics, edges and vertices without a matched DuckDB workload. Input preparation
is excluded and rechunked. `--rows` caps each case's configured size; the default
100,000 is a regression check. Use larger targeted workloads to substantiate
small timing differences. Omit `--baseline-plugin` for current-only profiling;
that checks repeatability and is not an independent correctness oracle.

### Python callback comparison

```bash
UV_NO_SYNC=1 uv run -m benchmarks python \
  --rows 10000 --threads 8 --output /tmp/h3-python.json
```

Uses `h3.api.basic_int` for integer cell IDs and produces a single result column
in both implementations. Timings include Python callback dispatch and Polars
result construction. They describe an end-to-end Polars workflow, not native
H3 call latency. List ordering is normalized only where the mathematical output
is unordered. Polygon coverage remains in the DuckDB suite. Neither Python nor
internal runs import DuckDB or install an extension.

### Optional plain Python and pandas baselines

```bash
UV_NO_SYNC=1 uv run --group benchmarking -m benchmarks baselines \
  --output /tmp/h3-baselines.json
```

This opt-in suite compares Polars, ordinary `h3.api.basic_str` Python list
comprehensions, and the [h3pandas accessor](https://github.com/DahnJ/H3-Pandas).
It stays out of `make bench` and the large DuckDB runs. The existing `python`
suite continues to measure H3 callbacks inside Polars; these answer different
questions.

Defaults are **10,000 scalar rows**, **1,000 list rows**, one excluded warmup,
three samples, **10 seconds per case**, and a **60-second suite worker budget**.
Each case runs sequentially in a fresh subprocess. Deadlines include worker
startup, input setup and validation; parent metadata/report I/O is additional.
An over-budget worker is killed and waited for, even if a native call has not
returned. Remaining cases are skipped when the suite budget is exhausted.

All three engines see exactly the same row count and logical inputs, using
string H3 IDs to match h3pandas. Cases cover indexing, parent lookup, resolution,
validity, disk and ring. List rows are capped by both `--rows` and `--list-rows`.
Do not compare Polars at one million rows with Python at one thousand rows and
call that a speedup; no timings are extrapolated to larger inputs.

Input preparation is recorded separately. Timings include computation and native
result construction: a Polars result column, a Python list, or a pandas result
Series selected from the accessor's output. Thus h3pandas' own DataFrame/index
handling is included. Conversion to a common validation representation happens
outside timing. These are framework workflows, not isolated H3 kernel calls.

Timed-out/skipped cases contain a reason and no performance numbers. The report
status is `partial` if any case is unfinished, and `compare` refuses it. Select
fewer functions or explicitly increase `--seconds-per-case` / `--budget-seconds`
to retry. Raising `--rows` alone cannot turn a slow run into an hour-long wait.
For example, to spend at most 30 seconds of worker time on two scalar cases:

```bash
UV_NO_SYNC=1 uv run --group benchmarking -m benchmarks baselines \
  --functions latlng_to_cell cell_to_parent --rows 10000 \
  --seconds-per-case 15 --budget-seconds 30 --output /tmp/h3-baselines-selected.json
```

## Migration and maintenance

`benchmarks.engine` and `benchmarks.large_engine` now print migration instructions;
the old unvalidated timing loops and benchmark classes have been removed.
Use `internal --rows N` in place of `large_engine --max-rows N`, and explicit row
counts instead of `engine --fast-factor`. Legacy names `int_hex_to_str`,
`str_hex_to_int` and `grid_path` become `int_to_str`, `str_to_int` and
`grid_path_cells` in the Python suite. The previously documented `h3-bench`
command was not registered; use `python -m benchmarks`.

`python -m benchmarks.head_to_head`, `benchmarks.regression`, and
`benchmarks.compare_results` remain supported for historical commands. The
comparison tool reads the original archived DuckDB reports as well as current
reports. New internal reports share the metadata/case/results schema with the
other suites; old internal JSON used a different format. Do not compare timings
across changed workloads or timing contracts. There is no aggregate speedup
across unlike operations.

The [benchmark notebook](../notebooks/benchmarking.ipynb) reads these saved
reports and displays per-operation samples; it does not implement another timer.

Add DuckDB cases in `workloads.py`, broad internal cases in
`internal_workloads.py`, and Python adapters in `python_api.py`. Shared timing,
plugin selection and report storage live in `common.py`. Keep contract tests in
`tests/test_benchmark_contracts.py`. Validate changes with those tests and small
real runs before expensive measurements.

## Storing results

Commit runners, correctness tests and concise reports with reproduction commands,
hardware/software details, source revisions and binary hashes. Write routine raw
JSON outside the repository; `benchmarks/results/*.json` and ZIPs are ignored.

For published claims, attach complete raw results to the PR and link from the
report. Include the archive SHA-256 and a per-file checksum manifest, and verify
a downloaded copy. Commit a raw baseline only when an automated comparison
consumes it, with a documented update policy and separate location. Treat small
differences in millisecond-scale operations as noise; use repeated samples and
larger workloads before claiming a modest speedup.
