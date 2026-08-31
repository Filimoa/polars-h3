# Benchmarks

This directory contains two benchmark drivers with different purposes. Always
build the Rust extension in release mode before running either one; development
build timings are not representative.

```bash
make install-release
```

## Cross-library benchmark

`benchmarks.engine` compares `polars-h3` with the DuckDB H3 extension and the
Python `h3` package. Use it to answer questions about how the libraries compare on the operations they have in common.

The benchmark covers a focused set of common operations. Its row counts are
grouped into basic, medium, and complex workloads. It also initializes the
DuckDB H3 extension, so it may require network access the first time it runs.

Run the complete comparison:

```bash
uv run -m benchmarks.engine
```

Run only `polars-h3`, reduce the workload, or select functions:

```bash
uv run -m benchmarks.engine --libraries plh3 --fast-factor 100
uv run -m benchmarks.engine --functions latlng_to_cell grid_ring
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

Use `benchmarks.engine` when the question is "How does `polars-h3` compare with
other H3 implementations?" Use `benchmarks.large_engine` when the question is
"Did this change make `polars-h3` faster?" The internal benchmark complements
the cross-library benchmark; it does not replace it.

For reliable before-and-after results, use the same machine, release profile,
row counts, selected functions, and iteration count for both builds. Treat
small differences in cases that complete in only a few milliseconds as timing
noise. Prefer several iterations and larger configured row counts before
claiming a modest speedup. Write generated JSON results to `/tmp` unless there
is a deliberate reason to preserve a result in the repository.
