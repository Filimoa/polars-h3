# Benchmarks

See the [2026-11-25 large-data results](results/2026-11-25-large-data.md)
for measured before/after timings, DuckDB comparisons, raw samples and limits.

## Large-data head-to-head

`benchmarks.head_to_head` is the stricter large-data comparison with DuckDB H3.
It uses identical deterministic inputs, matched thread counts, excluded warmups,
alternating engine order, and full-result validation outside every timed run.
It records raw wall/CPU samples, output sizes, setup costs, versions, SQL and
the actual plugin binary hash. It refuses to overwrite a previous results file.

After `make sync-bench`, run `make bench-h2h` to build and compare in one step.
Override `BENCH_OUTPUT` for each run and `BENCH_ARGS` to select workloads,
thread counts, or saved binaries. The default output is
`/tmp/polars-h3-head-to-head.json`.

```bash
make install-release
UV_NO_SYNC=1 uv run --group benchmarking -m benchmarks.head_to_head \
  --threads 8 --rows 5000000 --list-rows 250000 --polygon-rows 2000 \
  --iterations 5 --warmups 2 --output /tmp/h3-head-to-head.json
```

Install benchmark dependencies beforehand with `make sync-bench`. `UV_NO_SYNC=1`
keeps uv from rebuilding or replacing the release extension during measurement.
The driver loads the installed DuckDB H3 extension; pass `--install-extension`
once if it is missing. Repeat with `--threads 1` for single-thread comparisons.
For the strongest before/after comparison, retain the original release plugin
binary and pass `--baseline-plugin /absolute/path/to/baseline.abi3.so`.
The driver then rotates the original, current, and DuckDB implementations within
each trial on the exact same frame and records both plugin hashes. An explicit
`--plugin-path` can select the current binary as well. This avoids reinstalling
binaries between runs or relying on a dirty checkout's source version.
Summarize a paired result with:

```bash
UV_NO_SYNC=1 uv run -m benchmarks.compare_results \
  /tmp/h3-head-to-head.json /tmp/h3-head-to-head.json --baseline-engine baseline
```

Check all 46 operations from the broader internal suite against a saved binary:

```bash
UV_NO_SYNC=1 uv run -m benchmarks.regression \
  --baseline-plugin /absolute/path/to/baseline.abi3.so \
  --plugin-path /absolute/path/to/current.abi3.so \
  --rows 100000 --threads 8 --output /tmp/h3-regression.json
```

This driver compares exact values, dtypes and list ordering after every sample,
including APIs without an equivalent DuckDB benchmark. It rechunks inputs,
excludes warmups and interleaves the two implementations. Its smaller default
workloads are primarily a regression check; use larger targeted workloads to
substantiate small timing differences.

Use `--functions` to select cases; `--layout chunked` or `--layout sliced`
exercises Arrow layouts. `--null-every 7` adds nulls; operations with different
library null conventions will intentionally fail equivalence checks.

The timing modes answer different questions:

| Mode | Timed work |
| --- | --- |
| `resident` | Preloaded inputs, Polars DataFrame versus DuckDB temporary-table materialization. Excludes output export; includes native allocation/storage costs. |
| `arrow-materialized` | Preloaded native inputs; query and Arrow export in both engines. DuckDB first materializes a native result table, then exports it; both steps are timed. |
| `arrow-output` | Preloaded native inputs, full query execution and Arrow output in both engines. |
| `arrow-scan` | Polars native input versus DuckDB registered Arrow batches, with Arrow output. This measures an interchange scenario, not peak native DuckDB performance. |

The first two modes run by default. All four can be selected with `--modes`.
Direct DuckDB `SELECT`/Arrow fetching can use much less CPU parallelism than
native materialization; compare recorded CPU/wall ratios before attributing the
difference entirely to copying. `arrow-materialized` tests a parallel-friendly
DuckDB path while including its extra table allocation and export costs.
Input creation, conversion to Arrow, and ingestion into DuckDB's native table
are reported separately. Arrow input is batched (default 65,536 rows) so one
huge chunk does not artificially restrict DuckDB parallelism. No timing is
claimed to be pure H3 kernel time, and noisy identity-control timings are never
subtracted from operation timings. Identity projections expose zero-copy versus
materialization differences and should not count as H3 speedups.

The corpus covers valid Ohio cells, strings, nearby-cell relationships, list
expansion, WKB polygons, and a composed indexing/parent pipeline. Integer widths
are normalized for validation; unordered cell lists are sorted outside timing.
Floating results use relative tolerance 1e-7 and absolute tolerance 1e-9.
Validation fails loudly on mismatches. Numeric boundaries are deliberately not
compared with DuckDB's WKT representation. Pentagon, invalid-value and global
edge cases remain the responsibility of the correctness suite; these timings
must not be advertised as exhaustive geographic coverage.

The two additional drivers below cover legacy comparisons and internal operations. Always
build the Rust extension in release mode before running either one; development
build timings are not representative.

```bash
make install-release
```

## Cross-library benchmark

`benchmarks.engine` compares `polars-h3` with the DuckDB H3 extension and the
Python `h3` package. Use it to answer questions about how the libraries compare on the operations they have in common.
It runs one excluded warm-up by default and prints a direct DuckDB-to-`polars-h3`
speedup table when both libraries are selected. Timings include producing a
Polars result from each implementation, so interpret them as an end-to-end
comparison for a Polars-based workload rather than isolated H3 call latency.
The command also prints the concrete Polars, DuckDB, DuckDB H3 extension, and
Python H3 versions used by the run.

The benchmark covers a focused set of common operations, including native WKB
polygon-to-cell conversion in both engines. Polygon inputs are deterministic,
tract-sized WGS84 rectangles constructed before timing, and both engines
materialize the resulting `List(UInt64)` column. Row counts are grouped into
basic, medium, and complex workloads. It also initializes the DuckDB H3
extension, so it may require network access the first time it runs.

Run the complete comparison:

```bash
uv run --group benchmarking -m benchmarks.engine
```

Run only `polars-h3`, reduce the workload, or select functions:

```bash
uv run --group benchmarking -m benchmarks.engine --libraries plh3 --fast-factor 100
uv run --group benchmarking -m benchmarks.engine --functions latlng_to_cell grid_ring
uv run --group benchmarking -m benchmarks.engine --functions polygon_to_cells --iterations 5
```

## Internal performance benchmark

`benchmarks.large_engine` measures `polars-h3` only. Use it for before-and-after
optimization measurements and performance regression checks. It covers the
public Rust-backed expressions, uses deterministic Polars-generated data, and
assigns row counts per function so list- and geometry-producing operations do
not overwhelm memory.

Run all cases at their configured sizes:

```bash
uv run -m benchmarks.large_engine --iterations 3
```

For a faster local check, cap every case at the same maximum row count:

```bash
uv run -m benchmarks.large_engine --iterations 3 --max-rows 500000
```

Run selected cases and save the raw measurements:

```bash
uv run -m benchmarks.large_engine \
  --functions cell_to_children grid_ring directed_edge_to_cells \
  --iterations 5 \
  --output /tmp/polars-h3-benchmark.json
```

## Choosing a benchmark

Use `benchmarks.head_to_head` for measured performance claims against DuckDB
or paired before/after comparisons. Use `benchmarks.engine` for the older
Polars-oriented comparison including Python H3; its boundary case excludes
DuckDB because WKT formatting is different work from producing coordinates.
Use `benchmarks.large_engine` to explore additional public operations. Its
broader coverage complements the stricter driver.

For reliable before-and-after results, use the same machine, release profile,
row counts, selected functions, and iteration count for both builds. Treat
small differences in cases that complete in only a few milliseconds as timing
noise. Prefer several iterations and larger configured row counts before
claiming a modest speedup.

## Storing results

Commit benchmark runners, correctness tests, and concise reports with reproduction
commands, hardware/software details, source revisions, and binary hashes. Write
routine generated JSON to `/tmp` or another location outside the repository;
`benchmarks/results/*.json` and ZIP bundles are ignored.

For published performance claims, attach the complete raw-results archive to the
PR and link it from the committed report. Include the archive SHA-256 and a
per-file checksum manifest, and verify a downloaded copy before removing local
results. This preserves the samples and provenance without adding every run to
Git history. Only commit a raw baseline deliberately when an automated comparison
actually consumes it; give it a documented update policy and a separate location.
