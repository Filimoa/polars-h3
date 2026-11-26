# Second wrapper optimization pass — 2026-11-25

The next broad performance project should focus on **h3o's algorithms**. This
pass removed another substantial layer of Polars integration overhead, measured
53 workloads at several sizes and thread counts, and profiled the remaining
expensive paths. It leaves h3o 0.11.0 and the public Python API unchanged.

## Additional gains over the first optimized release

The baseline here is **`09a21f5`**, the already-optimized version in PR #28, not
the original implementation. The final implementation is **`71d11b2`**.
Eight threads, resident inputs, fully materialized Polars outputs; medians and
ranges of five samples after two warmups:

| Workload | Input rows | Previous release | This pass | Speedup | This pass range |
| --- | ---: | ---: | ---: | ---: | ---: |
| `string_cell_to_children` | 1,000,000 | 578.81 ms | 28.68 ms | **20.18×** | 27.78–30.20 ms |
| `cell_to_boundary` | 2,000,000 | 761.43 ms | 95.47 ms | **7.98×** | 95.06–96.23 ms |
| `get_num_cells` | 5,000,000 | 24.72 ms | 2.05 ms | **12.07×** | 1.80–2.30 ms |
| `child_pos_to_cell` | 5,000,000 | 36.98 ms | 6.62 ms | **5.58×** | 6.38–6.72 ms |
| `string_uncompact_cells` | 250,000 | 709.54 ms | 80.09 ms | **8.86×** | 78.50–82.79 ms |
| `vertex_to_latlng` | 5,000,000 | 422.56 ms | 125.81 ms | **3.36×** | 125.67–126.89 ms |
| `cell_to_local_ij` | 5,000,000 | 74.60 ms | 25.46 ms | **2.93×** | 24.73–25.81 ms |
| `cell_to_children` | 4,000,000 | 10.03 ms | 8.32 ms | **1.21×** | 8.21–8.56 ms |
| `grid_disk` | 1,500,000 | 90.53 ms | 82.43 ms | **1.10×** | 82.00–82.82 ms |

The input count is a row count, not the number of generated IDs. String child
expansion at one million rows produces seven million IDs; the separate
five-million-row numeric runs below produce 35 million child IDs and 185 million
disk IDs. No timings are extrapolated.

These compute-heavy controls remained essentially unchanged:

| Workload | Rows | Previous release | This pass |
| --- | ---: | ---: | ---: |
| `latlng_to_cell` | 5,000,000 | 131.39 ms | 130.99 ms |
| `cell_area` | 5,000,000 | 289.17 ms | 289.76 ms |
| `edge_length` | 5,000,000 | 155.30 ms | 155.74 ms |

At 100,000 rows with **one thread**, boundary generation improved 2.16×, string
child expansion 2.91×, and child-position conversion 1.47×. Grid disk was nearly
unchanged (1.01×). The eight-thread improvements include removal of serial work
and better scheduling; they should not be read as single-core algorithm gains.

## Updated original-implementation and DuckDB comparisons

These are fresh, matched runs against the original saved plugin and DuckDB H3,
separate from the already-optimized baseline above. Native output:

| Workload | Rows | Original | Final | DuckDB | Original → final |
| --- | ---: | ---: | ---: | ---: | ---: |
| `cell_to_children` | 5,000,000 | 176.56 ms | 11.75 ms | 48.50 ms | **15.03×** |
| `str_to_int` | 5,000,000 | 56.44 ms | 6.81 ms | 69.40 ms | **8.29×** |
| `cell_to_parent` | 5,000,000 | 19.79 ms | 2.76 ms | 5.49 ms | **7.18×** |
| `grid_disk` | 5,000,000 | 727.84 ms | 292.97 ms | 406.56 ms | **2.48×** |
| `string_cell_to_parent` | 5,000,000 | 285.98 ms | 24.93 ms | 144.75 ms | **11.47×** |
| `latlng_to_cell` | 5,000,000 | 166.58 ms | 132.29 ms | 216.69 ms | **1.26×** |

Including materialization and Arrow export, the five-million-row disk workload
measured **740.96 ms original, 309.20 ms final, and 1,065.66 ms DuckDB**: 2.40×
faster than the original and 3.45× faster than DuckDB. Loading and output
representation materially affect comparisons; native-output and Arrow-output
ratios are different contracts.

## What changed

- Boundary, vertex, edge, local-coordinate, child-position, and resolution outputs
  use bounded builders instead of whole-column temporary arrays or per-row Series.
- String lists format flattened values into reusable buffers, preserving offsets,
  nulls and ordering. Compaction reuses both its cell buffer and Series container.
- Expensive operations use smaller minimum batches. Compaction estimates work
  from the number of cells inside each row, rather than row count alone. Maximum
  batches remain capped at 65,536 rows.
- Disk/ring traversal validates directly into its loop and reserves capacity for
  common scalar radii, retaining the safe pentagon fallback.
- Numeric batches are assembled before string conversion, avoiding dtype conflicts
  when an entire batch is null. Empty/all-null outputs retain legacy dtypes,
  including `List(Null)` where the old collectors inferred it.

The internal suite retains all 46 historical cases and adds five string-list
cases and two cases with 2,401 cells in each of 128 rows. These catch costs hidden
by numeric-only benchmarks and by counting rows without considering list size.

## Why move into h3o next

Five-second CPU samples of the final release, with eight threads, identify:

| Workload | Dominant active frames |
| --- | --- |
| Latitude/longitude → cell | h3o `LatLng::to_cell`, bit rotations, trigonometric functions |
| Grid disk, radius 3 | h3o `neighbor_rotations` and `DiskDistancesUnsafe::next` |
| Polygon coverage | H3 tiling, neighbor traversal, coordinate conversion and containment predicates |

The samples were collected separately from timings. Waiting stacks and compiler
inlining mean these are hotspot evidence, not exact percentages or mathematical
speedup ceilings. Profile summaries, commands and binary hashes are in the raw
archive. The polygon wrapper was reviewed but left unchanged: tiling and geometry
work dominate, and its output buffer is needed for sorting and deduplication.

Later wrapper experiments showed diminishing returns. Fusing UInt64 pair parsing
changed large paired-operation timings by roughly -3% to +3%, so it was reverted.
Staging coordinate indexing through integers before string conversion gained
only about 3% at large scale and slowed small calls, so it was also reverted.
The retained disk changes improve the 1.5-million-row workload about 10% over the
previous optimized release.

Small and medium runs exposed scheduling regressions in paths, large sets,
boundaries, vertex coordinates and local IJ. Those were fixed before final
measurements. The 128-row large-set workload now remains parallel, while short
lists retain a cheap sequential path. Sub-millisecond timings remain noisy;
inspect absolute differences and sample ranges rather than ratios alone.

There is still room for workload-specific changes, such as avoiding repeated
operations or repeated inputs. For the measured general H3 workloads, the next
substantial targets are neighbor traversal and coordinate conversion inside
h3o, followed by polygon coverage. Keep these end-to-end benchmarks as a check
that library-level gains reach Python users.

## Validation and method

- **464 tests pass**, after rebuilding and installing the release extension.
  Formatting, Clippy, Ruff and Python type checks pass.
- **790 exact comparisons** against the saved optimized binary cover 53 workloads,
  native/signed/string IDs, five lengths including zero, invalid IDs, nulls,
  independent chunk boundaries and nonzero slices. String input is excluded from
  `int_to_str`, whose contract requires integers.
- Permanent regression tests cover whole-null prefixes/suffixes, typed all-null
  lists, pentagons, nested boundary offsets, compaction, local coordinates and
  out-of-range resolutions. Independent Python H3 oracles supplement the saved
  binary checks.
- All **53 cases** complete at row caps of 1,000, 16,384, 100,000 and 5,000,000 with
  eight threads, and at 100,000 with one thread. Every timed and warmup output is
  checked for exact values, dtypes and list order.
- Smoke checks pass all **33 DuckDB cases across four output modes**, **14 Python
  callback cases**, and **six bounded Python/h3pandas cases**. These small runs
  validate the harness and are not new headline speedup claims.

As documented in the benchmark guide, some cross-library null conventions differ.
An all-case nullable DuckDB probe stopped at a Boolean difference: Polars returns
false for null inputs where DuckDB returns null. That failed probe is preserved
separately, without a speedup claim; it was not silently normalized. Nullable
compatibility is covered by the exact saved-plugin checks and correctness tests.
The successful full DuckDB smoke matrix uses chunked, non-null inputs.

Machine: Apple M3 Max, 16 CPUs, 128 GiB RAM; macOS 26.6.2 ARM64. Rust 1.98.0,
Polars 1.44.1, polars-h3 0.7.1, DuckDB 1.5.5 with H3 extension v1.5.5/C H3 4.5.0,
PyArrow 25.0.1. Timed reports record clean source revision `71d11b2` and exact
binary hashes. Setup, validation and warmups are excluded; engines alternate
execution order. The deterministic Ohio/resolution-9 corpus is a performance
workload, not exhaustive geographic coverage. Peak RSS was not measured.

## Evidence and reproduction

[Download the checksummed raw evidence archive](https://github.com/user-attachments/files/35444550/polars-h3-wrapper-pass2-2026-11-25.zip), attached to
[PR #28](https://github.com/Filimoa/polars-h3/pull/28). It includes complete raw
results, the explicitly failed null-policy probe, correctness logs, profile
summaries and reproduction scripts. Raw JSON and plans remain outside Git.

Archive SHA-256: `979598e0fde581b7026b185c3a4fea5241993d280d2991656b8cd56d1ef28849`.

| Binary | SHA-256 |
| --- | --- |
| First optimized release | `641f3d597e97866b0eeb4332e6bc870442e36951eb2821607189a7d5c31f38a5` |
| Final release | `6fe5d2ad46e971b498c7ba89a85644d74d6d57a54a68fa9a8993308fcd1dc8e4` |
| Original implementation | `39f22c98c298396f15eb0e57787a844eaacdc00023cefb2130b01fda8bff393a` |

Build the revisions in release mode and retain distinct plugin binaries, as
explained in the [benchmark guide](../README.md). Then run:

```bash
UV_NO_SYNC=1 uv run -m benchmarks internal \
  --baseline-plugin /absolute/path/to/previous.abi3.so \
  --plugin-path /absolute/path/to/final.abi3.so \
  --rows 5000000 --threads 8 --output /tmp/h3-wrapper-large.json
```

`--rows` caps each case's configured size; it does not force every case to five
million rows. The archive contains commands for the other sizes, single-thread
runs, five-million-row DuckDB/list comparisons, and exact compatibility checks.
The [first-pass report](2026-11-25-large-data.md) retains the earlier original,
25-million-row, nullable/layout and transfer measurements with their provenance.
