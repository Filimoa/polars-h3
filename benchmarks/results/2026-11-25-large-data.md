# Large-data optimization results — 2026-11-25

The changes fuse validation with scalar operations, divide parallel work evenly into
batches capped at 65,536 rows, reuse string-formatting buffers, and build list values
directly in Arrow buffers. Disk traversal reuses scratch storage while retaining
the safe pentagon fallback. Public signatures, dtypes, null/invalid handling,
and list ordering are preserved. No h3o numerical algorithm was modified.

A subsequent [wrapper optimization pass](2026-11-25-wrapper-pass2.md) reports
additional gains over this optimized release, expanded compatibility checks,
and CPU profiles identifying the next h3o targets. The measurements below retain
their original provenance.

## Raw data

[Download the complete raw-results ZIP](https://github.com/user-attachments/files/35442368/polars-h3-benchmark-evidence-2026-11-25.zip),
attached to [PR #28](https://github.com/Filimoa/polars-h3/pull/28#issuecomment-7181441150).
It contains the original nine JSON files, a README, and `SHA256SUMS`.
The later [five-million-row list follow-up](#five-million-row-list-follow-up) has
a separate checksummed attachment.
The JSON files are preserved byte-for-byte; generated results are stored outside
Git while this report and the benchmark runners remain versioned.

Archive SHA-256: `670f4db6f8403a702983124957b3dd48062cce591b30115df55fc55990a36e8f`.
After extraction, run `shasum -a 256 -c SHA256SUMS` to verify each result file.

## Dependency sourcing

The performance branch now uses **crates.io h3o 0.11.0**. Vendoring and its
upstream-test, fuzzing and packaging infrastructure are deferred to the local
`experiment/h3o-core` branch. All 60 production source files in that snapshot
match the published crate byte-for-byte. The measurements below retain their
original provenance; registry-build verification is recorded separately.

## Method

Measurements used an Apple M3 Max (16 CPU cores, 128 GiB RAM), macOS 26.6.2
arm64, Rust 1.98.0, Polars 1.44.1, polars-h3 0.7.1, vendored h3o 0.11.0,
DuckDB 1.5.5 with H3 extension v1.5.5 / C H3 4.5.0, and PyArrow 25.0.1.
Both plugins were built with the same release profile and dependency lockfile.

The original plugin was saved before the Rust edits, then loaded alongside the
optimized plugin in each benchmark process. Its Rust source is `src/` at commit
`5200e0768d55c712bd1b99a9c22b4a25c7cf544b`; the unchanged vendored h3o was
already connected when it was built. Binary hashes are in every raw artifact.
Source archives and binaries remain under `/tmp/polars-h3-large-optimization`
on the measurement machine. The optimized source is the accompanying patch;
these measurements were collected from an uncommitted development tree before
the branch separation, not from a published release.

Each workload uses the same deterministic inputs for all engines, two excluded
warmups, five measured samples, matched thread counts, and rotating engine
order. Tables show medians. All output values are validated after every run,
outside timing. No competing builds or benchmark processes ran during timing.
Raw JSON retains each wall/CPU sample, min/max, versions, SQL, input/output
sizes, chunk counts, and separately measured setup costs. Byte counts describe
Polars buffers; peak process memory and native DuckDB storage are not measured.

`resident` times Polars DataFrame creation versus DuckDB temporary-table
creation from preloaded native inputs. It includes each engine's allocation
and storage costs, and excludes output export. `arrow-materialized` includes
query execution and Arrow export; DuckDB first creates a native result table
and then exports it, with both steps timed. These are different useful
contracts, not pure H3 kernel timings. Input generation, conversion and native
DuckDB loading are excluded and reported separately.

The benchmark also supports direct Arrow output and registered Arrow input.
The transfer experiment below shows the CPU parallelism difference between
direct SELECT/Arrow fetching and native materialization with eight configured
threads. That is why the main comparison includes the
parallel-friendly materialize-then-export path. It includes extra table costs;
it is not a claim that this path is fastest for every query. Identity controls
show representation/materialization overhead and are excluded from H3 wins.

## Scope and interpretation

The synthetic main corpus covers ordinary Ohio cells at resolution 9, nearby-cell pairs,
hex strings, radius-3 traversals, and tract-sized WKB rectangles. Scalar cases
use 5,000,000 rows, expanding-list cases 250,000, and polygons 2,000. List order
is normalized only where the cross-library contract is an unordered set;
floating comparisons use relative tolerance 1e-7 and absolute tolerance 1e-9.
The exact original/optimized regression driver separately checks list ordering.

Do not generalize these results to every region, resolution, polygon shape,
machine, query plan, or H3 API. The H3 C and h3o engines retain known numerical
differences. The preserved findings can be read with
`git show experiment/h3o-core:vendor/h3o/UPSTREAM.md`.
Fuzzing is useful evidence, not proof of equivalence. These optimizations do
not resolve those inherited findings. Invalid and nullable Boolean conventions
can differ between libraries; cross-library null tests select compatible APIs.

Small differences with overlapping sample ranges are treated as noise.
Directed-edge pairs and polygon conversion show no
meaningful before/after improvement in the main run. Area calculation improves
only modestly; its numerical algorithm is unchanged. The polygon implementation
was not changed. No timings from unlike operations are averaged into a single
headline speedup, and identity timings are never subtracted.

## Reproduce

Install dependencies with `make sync-bench`, and run `make bench-h2h` for the
default comparison. It builds the release extension first. For paired results,
save the original release plugin before applying the Rust changes, and run:

```bash
UV_NO_SYNC=1 uv run -m benchmarks.head_to_head \
  --threads 8 --rows 5000000 --list-rows 250000 --polygon-rows 2000 \
  --iterations 5 --warmups 2 \
  --baseline-plugin /tmp/polars-h3-large-optimization/baseline.abi3.so \
  --plugin-path /tmp/polars-h3-large-optimization/candidate3.abi3.so \
  --output /tmp/h3-new-run.json
UV_NO_SYNC=1 uv run -m benchmarks.compare_results \
  /tmp/h3-new-run.json /tmp/h3-new-run.json --baseline-engine baseline
```

The driver refuses to overwrite a result. Additional run settings are recorded
in each linked JSON artifact; `--functions`, `--threads`, `--rows`, `--layout`
and `--null-every` reproduce those variations. See the
[benchmark guide](../README.md) for all timing contracts and the 46-operation
regression driver.

## Main eight-thread results

[Raw measurements](#raw-data) (`2026-11-25-main-8t.json` in the archive). Both modes
validated all 33 cases.

### Native materialization

The optimized median is lower than DuckDB in 31 of these 31 H3
workloads. This describes this corpus and configuration, not universal superiority.

| Operation | Rows | Original ms | Optimized ms | DuckDB ms | Original / optimized |
| --- | ---: | ---: | ---: | ---: | ---: |
| cell_to_vertex | 5,000,000 | 80.80 | 67.95 | 113.04 | 1.19x |
| cell_to_lng | 5,000,000 | 86.09 | 73.01 | 84.44 | 1.18x |
| int_to_str | 5,000,000 | 139.87 | 25.50 | 75.50 | 5.49x |
| cell_to_children_size | 5,000,000 | 18.95 | 2.95 | 6.04 | 6.42x |
| directed_edge_to_cells | 250,000 | 1.98 | 2.00 | 4.57 | 0.99x* |
| str_to_int | 5,000,000 | 56.09 | 6.81 | 68.11 | 8.24x |
| grid_distance | 5,000,000 | 68.36 | 44.41 | 72.04 | 1.54x |
| cell_to_center_child | 5,000,000 | 18.94 | 3.00 | 4.77 | 6.32x |
| is_res_class_III | 5,000,000 | 17.83 | 2.09 | 4.02 | 8.54x |
| string_cell_to_parent | 5,000,000 | 269.45 | 24.03 | 142.16 | 11.22x |
| grid_ring | 250,000 | 17.60 | 7.56 | 38.45 | 2.33x |
| cells_to_directed_edge | 5,000,000 | 53.31 | 27.42 | 34.79 | 1.94x |
| is_pentagon | 5,000,000 | 17.96 | 2.20 | 4.81 | 8.18x |
| cell_area | 5,000,000 | 305.98 | 293.96 | 394.83 | 1.04x |
| get_directed_edge_origin | 5,000,000 | 25.31 | 2.85 | 3.74 | 8.89x |
| cell_to_latlng | 5,000,000 | 103.92 | 73.72 | 90.41 | 1.41x |
| get_directed_edge_destination | 5,000,000 | 28.71 | 9.35 | 11.73 | 3.07x |
| index_parent | 5,000,000 | 184.91 | 134.88 | 215.74 | 1.37x |
| cell_to_parent | 5,000,000 | 18.93 | 2.80 | 5.12 | 6.77x |
| grid_disk | 250,000 | 28.83 | 14.63 | 71.00 | 1.97x |
| latlng_to_cell | 5,000,000 | 163.93 | 132.09 | 212.18 | 1.24x |
| cell_to_children | 250,000 | 7.69 | 0.91 | 8.33 | 8.46x |
| are_neighbor_cells | 5,000,000 | 55.54 | 29.75 | 38.00 | 1.87x |
| latlng_to_cell_string | 5,000,000 | 184.19 | 153.67 | 286.91 | 1.20x |
| edge_length | 5,000,000 | 178.56 | 161.29 | 219.10 | 1.11x |
| cell_to_lat | 5,000,000 | 86.22 | 73.39 | 84.29 | 1.17x |
| cell_to_vertexes | 250,000 | 25.74 | 20.97 | 121.06 | 1.23x |
| polygon_to_cells | 2,000 | 11.03 | 11.04 | 152.70 | 1.00x* |
| is_valid_cell | 5,000,000 | 12.60 | 1.99 | 4.55 | 6.32x |
| origin_to_directed_edges | 250,000 | 6.69 | 1.05 | 4.48 | 6.37x |
| get_resolution | 5,000,000 | 16.57 | 2.37 | 3.88 | 6.99x |


### Computation and Arrow output

The optimized median is lower than DuckDB in 31 of these 31 H3
workloads. This describes this corpus and configuration, not universal superiority.

| Operation | Rows | Original ms | Optimized ms | DuckDB ms | Original / optimized |
| --- | ---: | ---: | ---: | ---: | ---: |
| cell_to_vertex | 5,000,000 | 89.02 | 68.36 | 118.79 | 1.30x |
| cell_to_lng | 5,000,000 | 93.29 | 73.54 | 89.49 | 1.27x |
| int_to_str | 5,000,000 | 173.11 | 57.13 | 156.25 | 3.03x |
| cell_to_children_size | 5,000,000 | 24.46 | 3.44 | 11.60 | 7.10x |
| directed_edge_to_cells | 250,000 | 2.02 | 2.04 | 7.39 | 0.99x* |
| str_to_int | 5,000,000 | 56.44 | 6.81 | 73.85 | 8.29x |
| grid_distance | 5,000,000 | 76.22 | 44.63 | 77.88 | 1.71x |
| cell_to_center_child | 5,000,000 | 24.77 | 3.25 | 10.31 | 7.63x |
| is_res_class_III | 5,000,000 | 23.98 | 2.43 | 13.83 | 9.88x |
| string_cell_to_parent | 5,000,000 | 305.64 | 59.18 | 222.08 | 5.16x |
| grid_ring | 250,000 | 17.38 | 7.75 | 53.12 | 2.24x |
| cells_to_directed_edge | 5,000,000 | 60.03 | 27.88 | 40.60 | 2.15x |
| is_pentagon | 5,000,000 | 24.37 | 2.62 | 18.50 | 9.32x |
| cell_area | 5,000,000 | 311.85 | 294.99 | 400.47 | 1.06x |
| get_directed_edge_origin | 5,000,000 | 30.77 | 3.25 | 9.36 | 9.47x |
| cell_to_latlng | 5,000,000 | 103.31 | 74.46 | 151.86 | 1.39x |
| get_directed_edge_destination | 5,000,000 | 35.11 | 9.57 | 17.50 | 3.67x |
| index_parent | 5,000,000 | 191.45 | 135.32 | 221.45 | 1.41x |
| cell_to_parent | 5,000,000 | 25.42 | 2.95 | 10.80 | 8.60x |
| grid_disk | 250,000 | 29.04 | 15.09 | 93.47 | 1.93x |
| latlng_to_cell | 5,000,000 | 170.47 | 132.29 | 218.41 | 1.29x |
| cell_to_children | 250,000 | 6.94 | 1.19 | 14.52 | 5.85x |
| are_neighbor_cells | 5,000,000 | 60.65 | 30.32 | 47.82 | 2.00x |
| latlng_to_cell_string | 5,000,000 | 228.96 | 183.11 | 366.56 | 1.25x |
| edge_length | 5,000,000 | 183.86 | 161.60 | 224.89 | 1.14x |
| cell_to_lat | 5,000,000 | 95.56 | 73.55 | 89.48 | 1.30x |
| cell_to_vertexes | 250,000 | 26.98 | 21.08 | 127.44 | 1.28x |
| polygon_to_cells | 2,000 | 11.23 | 11.18 | 151.81 | 1.00x* |
| is_valid_cell | 5,000,000 | 12.64 | 2.31 | 14.07 | 5.47x |
| origin_to_directed_edges | 250,000 | 6.76 | 1.09 | 10.65 | 6.21x |
| get_resolution | 5,000,000 | 23.25 | 2.75 | 7.67 | 8.44x |

An asterisk marks overlapping original/optimized sample ranges. Even without
overlap, a small difference is not necessarily practically meaningful.

Five million scalar values now typically produce 80 output chunks rather
than thousands. Identity controls remain in the raw data but are not H3 wins.

## Single-thread check

[Raw measurements](#raw-data) (`2026-11-25-single-thread.json` in the archive) cover 13
representative workloads in both timing modes, with the same row counts and five
samples. Native results below show how gains change without parallelism; the JSON also
contains Arrow-output results.

| Operation | Original ms | Optimized ms | DuckDB ms | Original / optimized |
| --- | ---: | ---: | ---: | ---: |
| grid_disk | 141.33 | 111.80 | 137.10 | 1.26x |
| cell_to_children | 12.23 | 3.83 | 15.69 | 3.19x |
| string_cell_to_parent | 300.39 | 171.76 | 1002.31 | 1.75x |
| are_neighbor_cells | 235.97 | 223.30 | 291.70 | 1.06x |
| cell_area | 2234.14 | 2243.64 | 2808.99 | 1.00x* |
| cell_to_parent | 49.76 | 18.98 | 31.25 | 2.62x |
| get_directed_edge_destination | 84.27 | 68.30 | 77.10 | 1.23x |
| grid_ring | 79.96 | 49.80 | 72.60 | 1.61x |
| int_to_str | 270.80 | 198.68 | 524.00 | 1.36x |
| str_to_int | 54.21 | 50.08 | 478.90 | 1.08x |
| latlng_to_cell | 1054.61 | 1007.87 | 1506.84 | 1.05x |
| index_parent | 1106.66 | 1027.90 | 1533.87 | 1.08x |
| get_directed_edge_origin | 56.71 | 19.98 | 21.25 | 2.84x |


## Twenty-five million rows

[Raw measurements](#raw-data) (`2026-11-25-large-25m.json` in the archive) cover six
scalar/composed workloads at eight threads, with full validation of every output.

| Operation | Original ms | Optimized ms | DuckDB ms | Original / optimized |
| --- | ---: | ---: | ---: | ---: |
| str_to_int | 287.10 | 33.31 | 323.34 | 8.62x |
| index_parent | 904.65 | 674.19 | 1025.15 | 1.34x |
| string_cell_to_parent | 1324.72 | 113.94 | 676.43 | 11.63x |
| cell_to_parent | 91.41 | 12.70 | 22.76 | 7.20x |
| latlng_to_cell | 810.28 | 658.96 | 1007.70 | 1.23x |
| are_neighbor_cells | 283.29 | 150.86 | 177.14 | 1.88x |

### Including Arrow output

| Operation | Original ms | Optimized ms | DuckDB ms | Original / optimized |
| --- | ---: | ---: | ---: | ---: |
| str_to_int | 286.76 | 34.21 | 350.47 | 8.38x |
| index_parent | 916.30 | 674.93 | 1052.89 | 1.36x |
| string_cell_to_parent | 1528.36 | 286.64 | 1070.02 | 5.33x |
| cell_to_parent | 96.17 | 13.80 | 49.49 | 6.97x |
| latlng_to_cell | 817.47 | 659.08 | 1035.13 | 1.24x |
| are_neighbor_cells | 293.02 | 158.64 | 224.86 | 1.85x |

The indexing/parent pipeline processes about 37.1 million rows
per second in this native-materialization scenario.

## Transfer and execution paths

[Raw measurements](#raw-data) (`2026-11-25-transfer.json` in the archive) use one
million rows, eight threads and all four timing contracts. CPU/wall is the median of
process CPU/wall time ratios, an approximate measure of CPU parallelism for the whole
timed call. It includes more than the H3 kernel.

| Operation | Mode | Polars ms | DuckDB ms | DuckDB CPU / wall |
| --- | --- | ---: | ---: | ---: |
| latlng_to_cell | resident | 26.61 | 44.81 | 7.21 |
| latlng_to_cell | arrow-materialized | 26.78 | 46.79 | 7.03 |
| latlng_to_cell | arrow-output | 27.02 | 267.59 | 1.68 |
| latlng_to_cell | arrow-scan | 27.85 | 268.95 | 1.33 |
| identity_string | resident | 0.04 | 3.66 | 6.67 |
| identity_string | arrow-materialized | 6.53 | 17.95 | 2.40 |
| identity_string | arrow-output | 6.29 | 13.77 | 1.28 |
| identity_string | arrow-scan | 6.70 | 16.65 | 1.16 |
| string_cell_to_parent | resident | 5.08 | 30.63 | 7.18 |
| string_cell_to_parent | arrow-materialized | 11.82 | 45.59 | 5.24 |
| string_cell_to_parent | arrow-output | 11.95 | 180.92 | 1.36 |
| string_cell_to_parent | arrow-scan | 11.90 | 188.11 | 1.22 |
| identity_u64 | resident | 0.06 | 0.82 | 4.25 |
| identity_u64 | arrow-materialized | 0.07 | 2.08 | 2.64 |
| identity_u64 | arrow-output | 0.08 | 1.41 | 1.81 |
| identity_u64 | arrow-scan | 0.08 | 1.77 | 1.93 |

A large direct-Arrow gap must not be attributed entirely to data copying.
Compare native execution and the materialize-then-export path as well. Setup
costs are single observations recorded separately, not steady-state medians.

## Layout and correctness checks

The [chunked](#raw-data) (`2026-11-25-chunked-null.json` in the archive) and
[sliced](#raw-data) (`2026-11-25-sliced-null.json` in the archive) runs use one million
scalar rows and 50,000 expanding-list rows, with a null every seventh row. All seven
selected APIs pass full original/optimized/DuckDB comparisons in both modes. The sliced
case has a nonzero, non-byte-aligned validity offset.

The [46-operation regression](#raw-data) (`2026-11-25-regression.json` in the archive)
uses up to 100,000 rows per case and validates exact values, dtypes and list order after
every sample. It covers additional public operations without a matched DuckDB case.

This check caught an intermediate scheduling regression: seven batches left a
worker idle on eight threads. Rounding batch counts to worker multiples fixed
it. Final 100K-row area timings are 6.55 ms original and
5.96 ms optimized. Small slowdowns on unchanged operations
(such as average area lookup) have overlapping ranges and are not treated as
material regressions.

During the original campaign, checks passed: `make fmt`, `make lint`, `make install`, release build,
`make test` (413 tests against the release extension), `make test-h3o`
(113 unit + 924 integration + 95 documentation tests), and `make test-sdist`
(extracted build and bundled license verification). The installed extension
at that point matched the measured release build. The vendoring-specific
targets and workflow are now preserved on `experiment/h3o-core`. GitHub workflows were configured locally;
remote CI was not run in this session. Two inherited fuzz mismatches remain
documented in the vendored provenance file; they were not hidden or weakened.

Original optimized plugin SHA-256: `caf3e6de9e3fbe0804b6f21de194a78e0bc952de4fb81884e4289f8a829cb5a8`.

## Registry-backed branch verification

After separating vendoring to `experiment/h3o-core`, the performance branch
was rebuilt against crates.io h3o 0.11.0. Cargo metadata confirms registry
resolution; all 60 production source files match the preserved vendored copy.
Formatting, lint and all 413 Python tests pass on the rebuilt extension.
The installed extension is the registry-backed release build.

[Exact comparisons](#raw-data) (`2026-11-25-registry-equivalence.json` in the archive)
against the previously measured optimized vendored binary pass all 46 operations,
including dtypes and list ordering. The [eight-workload spot-check](#raw-data)
(`2026-11-25-registry-head-to-head.json` in the archive) repeats five samples after two
warmups at eight threads against the original baseline and DuckDB in both native and
Arrow-materialization modes.

Native results confirm the earlier gains without vendoring:

| Operation | Rows | Original ms | Registry-backed ms | Speedup |
| --- | ---: | ---: | ---: | ---: |
| str_to_int | 5,000,000 | 57.26 | 6.55 | 8.74x |
| cell_to_parent | 5,000,000 | 18.85 | 2.82 | 6.68x |
| cell_to_children | 250,000 | 6.96 | 0.96 | 7.21x |
| get_directed_edge_origin | 5,000,000 | 24.54 | 2.82 | 8.71x |
| string_cell_to_parent | 5,000,000 | 264.38 | 23.74 | 11.14x |
| grid_disk | 250,000 | 29.22 | 14.79 | 1.98x |
| latlng_to_cell | 5,000,000 | 163.72 | 133.00 | 1.23x |
| index_parent | 5,000,000 | 184.79 | 134.76 | 1.37x |

Registry-backed plugin SHA-256: `641f3d597e97866b0eeb4332e6bc870442e36951eb2821607189a7d5c31f38a5`.


## Five-million-row list follow-up

The earlier list workloads used 250,000 input rows to limit output size. This
follow-up measures **5,000,000 input rows** for both `cell_to_children` and
`grid_disk`, using the same saved original and registry-backed optimized plugins,
eight threads, two warmups, and five measured samples. Resolution is 9; children
use resolution 10 and disks use radius 3. Hardware and engine versions match the
registry-backed run above. The earlier results remain unchanged as historical
evidence; these are direct measurements, not extrapolations.

### Native output at five million rows

| Operation | Original ms | Optimized ms | DuckDB ms | Original / optimized | DuckDB / optimized |
| --- | ---: | ---: | ---: | ---: | ---: |
| cell_to_children | 176.04 | 12.45 | 58.57 | 14.14x | 4.70x |
| grid_disk | 700.88 | 307.83 | 405.46 | 2.28x | 1.32x |

### Including Arrow output at five million rows

| Operation | Original ms | Optimized ms | DuckDB ms | Original / optimized | DuckDB / optimized |
| --- | ---: | ---: | ---: | ---: | ---: |
| cell_to_children | 175.20 | 12.53 | 190.53 | 13.98x | 15.20x |
| grid_disk | 709.66 | 327.79 | 1017.03 | 2.16x | 3.10x |

Optimized native samples range from 12.11–13.33 ms for children and
303.27–314.83 ms for disks. The outputs contain 35 million child IDs and
185 million disk IDs; estimated Polars result buffers are 320 MB and 1.52 GB
respectively (decimal units, not peak process memory).

The larger workload improves the measured before/after ratio for children to
14.14x and disks to 2.28x. DuckDB also scales differently: the native grid-disk
advantage is 1.32x here, compared with 4.79x at 250,000 rows in the registry
spot-check. Including materialize-then-Arrow output, it is 3.10x. Row count and
output handling materially affect cross-library comparisons.

Full-output validation initially dominated the run because it boxed and sorted
hundreds of millions of IDs in Python. That incomplete attempt was stopped.
The completed run uses native equality and bounded NumPy sorting for fixed-width
integer lists, with the general null/ragged/string comparison retained. Every
value, duplicate and list boundary is still checked after every output, outside
the query timer. Query execution and the measured plugin binaries are unchanged.
The validator passed targeted mismatch tests and the full 442-test suite.

Benchmark source revision: `4ed5145508bce31909f4a11716a7de2c04eadb2c` (clean tree).
[Download the follow-up raw results](https://github.com/user-attachments/files/35443625/polars-h3-list-5m-2026-11-25.zip),
attached to [PR #28](https://github.com/Filimoa/polars-h3/pull/28#issuecomment-7182193437).
The ZIP contains `2026-11-25-list-5m.json`, a README, and `SHA256SUMS`; its downloaded
bytes were verified against the original result file.
Archive SHA-256: `d27645ba53fb2126e57c90475d7fcf58d2a3b9a423036f39a8b37b210f32094a`.

Reproduce using the saved original and registry-backed binaries:

```bash
UV_NO_SYNC=1 uv run -m benchmarks duckdb \
  --functions cell_to_children grid_disk \
  --rows 5000000 --list-rows 5000000 --threads 8 \
  --iterations 5 --warmups 2 \
  --baseline-plugin /tmp/polars-h3-large-optimization/baseline.abi3.so \
  --plugin-path /tmp/polars-h3-dependency-split/registry.abi3.so \
  --output /tmp/h3-list-5m-new.json
```
