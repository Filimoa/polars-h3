# Kernel performance profile

For the current cross-library results, see [DuckDB comparison](#duckdb-comparison-after-both-optimization-passes).

The latest implementation and measurements are in [Second pass](#second-pass-hierarchy-strings-and-scalar-kernels). Earlier sections preserve the first-pass implementation and results as historical comparisons.

The change fuses H3 cell validation with consumption in inspection and scalar hierarchy kernels, instead of materializing a full intermediate vector. Coordinate indexing reads the existing Float64 columns directly (Float32 still casts once) and constructs its output in a single pass. Coordinate conversion, integer-to-string conversion, and child-position lookup use ordered parallel batches: parallel work starts at 4,096 rows, the batch-size target is at least 1,024 rows, and there are at most as many batches as Rayon workers. Smaller calls run on the caller thread. This keeps parallel throughput while preventing per-task Polars arrays from multiplying throughout a pipeline.

Public signatures, actual output dtypes, validation, null behavior, and row order remain compatible. Other traversal, geometry, and boundary algorithms are unchanged. Hexadecimal formatting still allocates a string per value; that separate optimization remains future work.

## Method

Run on macOS 26.6.2 arm64, Python 3.12.5, Polars 1.44.1, with both `POLARS_MAX_THREADS=16` and `RAYON_NUM_THREADS=16`. Both shared libraries were built from source with the existing optimized release profile and LTO. Each library runs in a fresh process; benchmark and profiler processes never run concurrently with a build or another benchmark.

`benchmarks/kernel_profile.py` measures 17 kernels/pipelines: 1,000-row contiguous batches and 1,000,000-row contiguous, fragmented, and nullable inputs, in eager and lazy modes (136 cases). Fragmentation is fixed at 256 input chunks for both binaries. Nullable inputs contain deterministic nulls and invalid cells/coordinates. Input generation and expression preparation are excluded from kernel timing. Pipeline timing includes indexing and both downstream expressions. Three warmups precede seven timed executions per case; reported wall times are medians. Output disposal and output hashing occur outside the timed region. Process CPU time is recorded separately.

Comparison checks require identical output schemas, row hashes, and input chunk layouts. The row hashes are a broad equivalence check; the Python suite separately checks actual values against h3-py, including negative and malformed indexes, pentagons, nonzero-offset slices, differing coordinate chunk boundaries, float dtypes, empty/all-null inputs, and eager/lazy/streaming execution. A regression test bounds chunk growth in an indexing pipeline without making timing assertions.

## Results

Selected lazy-query medians, one million rows, in milliseconds:

| Operation | Input layout | Before | After | Speedup |
| --- | --- | ---: | ---: | ---: |
| Resolution lookup | Contiguous | 6.49 | 2.76 | 2.35× |
| Parent lookup | Contiguous | 6.90 | 3.80 | 1.81× |
| Child-position lookup | Contiguous | 6.43 | 0.88 | 7.30× |
| Latitude/longitude to cell | Contiguous | 27.14 | 22.44 | 1.21× |
| Cell to latitude/longitude pair | Contiguous | 16.68 | 14.64 | 1.14× |
| Integer to hexadecimal string | Contiguous | 31.56 | 4.89 | 6.45× |
| Index → parent + resolution pipeline | Contiguous | 241.89 | 26.00 | 9.30× |
| Resolution lookup | 256 chunks | 25.60 | 0.64 | 39.91× |
| Latitude/longitude to cell | 256 chunks | 90.30 | 17.22 | 5.25× |
| Index → parent + resolution pipeline | 256 chunks | 939.52 | 17.67 | 53.16× |

The fragmented resolution output dropped from about 201,500 chunks to 256. Contiguous indexing dropped from about 8,247 chunks to 16; downstream pipeline columns now each have 16 chunks on contiguous input and 256 on fragmented input. Original chunk counts vary with task scheduling; input layouts were fixed for these comparisons.

Process CPU time also fell: the fragmented pipeline went from 10,268.90 ms to 256.66 ms per query, and fragmented resolution lookup from 296.35 ms to 7.74 ms. These are summed CPU times across threads, distinct from wall time. The full benchmark process's peak resident memory decreased from 3.63 GiB to 0.39 GiB (3,899,998,208 to 421,855,232 bytes). That memory measurement includes setup, every benchmark case, and allocator retention; it is not an isolated per-kernel allocation measurement.

### Batch-size sweep and tradeoffs

A second comparison covers four affected kernels in eager and lazy modes at 2,048, 4,095, 4,096, 8,192, 16,384, 32,768, 65,536, and 100,000 rows (64 cases, three warmups and nine measurements each). Together with the main matrix, all 200 cases match input chunk counts, output schemas, and result fingerprints.

Eager latitude/longitude indexing illustrates the final cutoff:

| Rows | Before (ms) | After (ms) | Speedup |
| ---: | ---: | ---: | ---: |
| 2,048 | 0.683 | 0.461 | 1.48× |
| 4,095 | 0.749 | 0.890 | 0.84× |
| 4,096 | 0.725 | 0.344 | 2.11× |
| 8,192 | 1.123 | 0.424 | 2.65× |
| 16,384 | 1.495 | 0.622 | 2.40× |
| 32,768 | 2.173 | 0.992 | 2.19× |
| 65,536 | 3.029 | 1.816 | 1.67× |
| 100,000 | 3.895 | 2.346 | 1.66× |

There is a retained small-batch tradeoff: at 4,095 rows, serial coordinate indexing is approximately 0.14 ms (19%) slower in eager mode, and 0.13 ms (17%) slower in lazy mode. The cutoff avoids starting another worker-pool operation for small partitions already being processed by Polars. This policy favors pipelines and throughput, and the table makes its latency cost near the cutoff explicit. All main-matrix medians and the other size-sweep medians were faster in the final run; these measurements remain specific to this hardware and workload.

The initial implementation used a 16,384-row batch target, which substantially slowed medium coordinate inputs. The sweep caught that regression before delivery. An initially serial child-position implementation also showed an approximately 8% contiguous-input regression in alternating before/after rechecks; moving it onto the coarse parallel path resolved it. Small differences should be interpreted cautiously: even the unchanged validity control varied between the exploratory runs.

## 25-million-row follow-up

Measured on the same machine with the same preserved release binaries and 16 threads in each pool. This comparison covers all 17 operations/pipelines in lazy mode, with contiguous input and input split into 256 chunks (34 cases). Each case has two warmups and five timed runs; values below are median wall times in milliseconds. All 34 output schemas, fingerprints, and input chunk layouts match between builds. Input generation and output disposal/hashing remain outside timing.

### Contiguous input

| Operation | Before (ms) | After (ms) | Speedup |
| --- | ---: | ---: | ---: |
| `get_resolution` | 79.35 | 77.61 | 1.02× |
| `get_resolution_string` | 312.56 | 279.44 | 1.12× |
| `is_valid_cell` | 61.97 | 66.00 | 0.94× |
| `is_pentagon` | 84.70 | 68.82 | 1.23× |
| `is_res_class_III` | 88.04 | 65.43 | 1.35× |
| `cell_to_parent` | 87.36 | 98.38 | 0.89× |
| `cell_to_parent_string` | 1,362.31 | 1,327.88 | 1.03× |
| `cell_to_center_child` | 86.33 | 97.19 | 0.89× |
| `cell_to_children_size` | 86.10 | 100.97 | 0.85× |
| `cell_to_child_pos` | 87.40 | 16.08 | 5.44× |
| `latlng_to_cell` | 548.39 | 392.57 | 1.40× |
| `latlng_to_cell_string` | 615.48 | 475.21 | 1.30× |
| `cell_to_lat` | 279.67 | 222.33 | 1.26× |
| `cell_to_lng` | 277.17 | 218.52 | 1.27× |
| `cell_to_latlng` | 371.13 | 223.53 | 1.66× |
| `int_to_str` | 689.22 | 88.71 | 7.77× |
| `index_parent_resolution` | 1,452.50 | 432.02 | 3.36× |

### Input split into 256 chunks

| Operation | Before (ms) | After (ms) | Speedup |
| --- | ---: | ---: | ---: |
| `get_resolution` | 64.10 | 8.80 | 7.28× |
| `get_resolution_string` | 87.53 | 23.79 | 3.68× |
| `is_valid_cell` | 5.48 | 6.93 | 0.79× |
| `is_pentagon` | 55.73 | 6.83 | 8.15× |
| `is_res_class_III` | 68.28 | 6.97 | 9.79× |
| `cell_to_parent` | 84.23 | 8.94 | 9.43× |
| `cell_to_parent_string` | 133.33 | 115.66 | 1.15× |
| `cell_to_center_child` | 54.87 | 9.49 | 5.78× |
| `cell_to_children_size` | 80.71 | 9.12 | 8.85× |
| `cell_to_child_pos` | 84.53 | 17.70 | 4.78× |
| `latlng_to_cell` | 552.26 | 413.63 | 1.34× |
| `latlng_to_cell_string` | 1,015.64 | 483.42 | 2.10× |
| `cell_to_lat` | 275.12 | 258.06 | 1.07× |
| `cell_to_lng` | 245.05 | 227.61 | 1.08× |
| `cell_to_latlng` | 261.50 | 228.72 | 1.14× |
| `int_to_str` | 116.52 | 90.28 | 1.29× |
| `index_parent_resolution` | 8,995.22 | 464.98 | 19.35× |

The indexing → parent + resolution pipeline improves from **1.45 s to 0.43 s (3.36×)** for contiguous input and **9.00 s to 0.46 s (19.35×)** for fragmented input. Whole-process peak resident memory decreases from **9.43 GiB to 3.61 GiB**, about 62%. This includes input generation, all cases, and allocator retention; it is not per-operation memory or an isolated measure of kernel allocation.

There are real large-contiguous-input tradeoffs. To check the initially slower hierarchy results, a separate comparison ran the optimized build first and baseline second, using three warmups and nine timed runs. Its five cases also match schemas, fingerprints, and input chunks:

| Contiguous operation, recheck | Before (ms) | After (ms) | Change |
| --- | ---: | ---: | ---: |
| `get_resolution` | 79.13 | 71.44 | 9.7% faster |
| `is_valid_cell` | 62.22 | 62.16 | 0.1% faster |
| `cell_to_parent` | 85.71 | 91.93 | 7.3% slower |
| `cell_to_center_child` | 85.62 | 96.89 | 13.2% slower |
| `cell_to_children_size` | 89.32 | 100.58 | 12.6% slower |

The parent, center-child, and children-count regressions persist at approximately 7–13% in the reverse-order recheck. These kernels now process each plugin call serially; on a single 25-million-row chunk, reduced allocation overhead does not fully offset the loss of inner parallelism. With 256 input chunks, Polars can parallelize those calls and all three are substantially faster. No further kernel changes were made for this measurement request. `is_valid_cell` is an unchanged control; its recheck is effectively equal, illustrating that small differences between full-suite runs can be environmental.

Chunk counts also explain why speedups differ from the million-row experiment. Each of the 256 input chunks now contains about 97,657 rows, above the plugin's parallel threshold. Expensive optimized kernels therefore produce 4,096 output chunks (16 per input chunk), while cheap fused kernels produce 256. The contiguous optimized pipeline produces 16 chunks per output column, versus roughly 2.4–2.6 million in its baseline result. These output chunk counts are taken from the untimed verification execution and can vary with baseline scheduling.

Raw artifacts are `baseline-25m.json`, `optimized-25m.json`, and the corresponding `*-25m-recheck.json` and `.log` files under `/tmp/polars-h3-kernel-profile/`. Reproduce the main comparison by running this command separately for `baseline.so` and `optimized.so`, changing the output name accordingly:

    UV_CACHE_DIR=/tmp/polars-h3-uv-cache UV_OFFLINE=true POLARS_MAX_THREADS=16 RAYON_NUM_THREADS=16 uv run --no-sync -m benchmarks.kernel_profile --plugin /tmp/polars-h3-kernel-profile/baseline.so --rows 25000000 --layouts contiguous fragmented --modes lazy --iterations 5 --warmups 2 --output /tmp/polars-h3-kernel-profile/baseline-25m.json

For the contiguous recheck, use `--layouts contiguous --functions get_resolution is_valid_cell cell_to_parent cell_to_center_child cell_to_children_size --iterations 9 --warmups 3` with each binary in reverse order and distinct output filenames. These are measured results for the deterministic benchmark inputs, not extrapolations or a guarantee for every 25-million-row workload.

## CPU sampling

The macOS native `sample` tool captures five seconds at a 1 ms interval from a task-owned process repeatedly evaluating either `get_resolution` or `latlng_to_cell` on fixed fragmented million-row input. Workload setup finishes before sampling starts. Sampled executions are separate from timed measurements.

In the original resolution kernel, active stacks include the plugin's Rayon bridge/join scheduling, parallel linked-list array collection, allocation, and Arrow FFI construction. In the optimized kernel, that inner parallel collection path is eliminated; work shifts to the resolution plugin and direct Arrow iterator/array construction. Polars still schedules its own partitions. Sleeping and synchronization samples are not interpreted as CPU-time percentages, and the call counts during sampling are not used as speedup measurements.

The final coordinate sample's active stacks are led by `h3o::LatLng::to_cell`, H3 index rotation, and trigonometric functions (`atan2`, sine/cosine, `tan`, and `acos`). Both final sample workloads recorded the same binary hash as the final timing comparison.

## Reproduce

From the repository root, retain the unmodified release binary before making source changes:

    UV_CACHE_DIR=/tmp/polars-h3-uv-cache UV_NO_SYNC=1 UV_OFFLINE=true make install-release
    mkdir -p /tmp/polars-h3-kernel-profile
    cp polars_h3/polars_h3.abi3.so /tmp/polars-h3-kernel-profile/baseline.so
    POLARS_MAX_THREADS=16 RAYON_NUM_THREADS=16 uv run --no-sync -m benchmarks.kernel_profile --plugin /tmp/polars-h3-kernel-profile/baseline.so --output /tmp/polars-h3-kernel-profile/before.json

After the source changes, rebuild and repeat with the new binary:

    UV_CACHE_DIR=/tmp/polars-h3-uv-cache UV_NO_SYNC=1 UV_OFFLINE=true make install-release
    cp polars_h3/polars_h3.abi3.so /tmp/polars-h3-kernel-profile/optimized.so
    POLARS_MAX_THREADS=16 RAYON_NUM_THREADS=16 uv run --no-sync -m benchmarks.kernel_profile --plugin /tmp/polars-h3-kernel-profile/optimized.so --output /tmp/polars-h3-kernel-profile/after.json

Repeat the batch-size sweep for each preserved binary:

    POLARS_MAX_THREADS=16 RAYON_NUM_THREADS=16 uv run --no-sync -m benchmarks.kernel_profile --plugin /tmp/polars-h3-kernel-profile/optimized.so --rows 2048 4095 4096 8192 16384 32768 65536 100000 --layouts contiguous --modes eager lazy --functions latlng_to_cell cell_to_lat int_to_str cell_to_child_pos --iterations 9 --warmups 3 --output /tmp/polars-h3-kernel-profile/optimized-size-sweep.json

For a native CPU sample, run a dedicated workload in one terminal:

    POLARS_MAX_THREADS=16 RAYON_NUM_THREADS=16 uv run --no-sync -m benchmarks.kernel_profile --plugin /tmp/polars-h3-kernel-profile/optimized.so --repeat get_resolution --rows 1000000 --layouts fragmented --modes lazy --duration 30 --ready-file /tmp/polars-h3-profile.ready

After the ready file is written, sample that PID from another terminal:

    sample "$(cat /tmp/polars-h3-profile.ready)" 5 1 -file /tmp/polars-h3-profile.txt

On other systems, the repeat mode can be used with the platform's native profiler. Native sampling may require permission to inspect the workload process.

## Artifacts and validation

Raw JSON timings, execution logs, native samples, and preserved shared libraries are in `/tmp/polars-h3-kernel-profile/`. These are local experimental artifacts, not checked-in binaries. `before.json` and `after.json` include exact library SHA-256 hashes and environment metadata; `baseline-size-sweep.json` and `optimized-size-sweep.json` contain the final size sweep. `baseline-*-sample.txt` and `optimized-*-sample.txt` contain native profiles. Native sample logs can be large because they include all worker-thread stacks.

The baseline source was repository commit `72457e4`, without Rust changes. Binary SHA-256 values:

    baseline: 9695e7f94a8602fa606c20556c6d8ad0749a560faf3fcf1fae72d0ec5f999d86
    optimized: b3ea8cc4cc8ec47f6c1a9b52f92aa1424c5d0b4c5bce2b7420313333673fe4c0

`make fmt`, `make lint`, `make install`, and `make test` passed, including all 306 tests against the rebuilt development extension. The final release was rebuilt with `make install-release` and verified against the saved optimized binary before all 200 final comparisons. All 306 tests also passed against that final release. That validation describes the first-pass release; the currently installed release is identified in the second-pass section below.

## Second pass: hierarchy, strings, and scalar kernels

This pass compares the **previous optimized release** against the next optimized release. Its before values are not the original unoptimized library. Measurements use the same machine, Python/Polars versions, optimized LTO build settings, and 16 threads in each pool as the first pass.

### Implementation

Cheap parent, center-child, children-count, edge-origin, and vertex-validity calls now start bounded parallel work at **262,144 rows**. Smaller calls borrow the original Series directly and remain serial, allowing Polars to parallelize its existing partitions. Parallel calls still produce at most one output chunk per Rayon worker. More expensive scalar kernels retain the 4,096-row activation threshold and 1,024-row minimum batch target.

Eight additional kernels now fuse parsing with consumption and avoid whole-column intermediate vectors: `get_directed_edge_origin`, `get_directed_edge_destination`, `are_neighbor_cells`, `cells_to_directed_edge`, `cell_to_vertex`, `is_valid_vertex`, `child_pos_to_cell`, and `grid_distance`. Paired kernels borrow and advance the second column independently, preserving alignment even when its Arrow chunk boundaries differ. Existing zip-length behavior is preserved; this change does not introduce scalar broadcasting.

`HexStringBuilder` reuses one String with capacity 16 per builder, instead of allocating a formatted String for every index. It serves integer-to-string conversion, coordinate string output, scalar hierarchy string output, and shared list string conversion. Formatting stays lowercase and unpadded. Hierarchy conversion to the requested dtype occurs inside each worker batch. Existing cell parsing remains directly implemented to limit changes to previously tuned kernels; generic fused parsing is shared by the new edge/vertex paths.

Public signatures, actual dtypes, ordering, and null/invalid-value handling remain compatible. List expansion, boundary, geometry, and metric algorithms were not changed in this pass. Shared list formatting changed, but list algorithms have not received a separate speedup claim.

### Measurements

The extended benchmark adds deterministic neighboring children, directed edges, vertices, and child-position columns outside the timed region. Grid-distance results below therefore describe neighboring cells, not arbitrary long-distance or failing paths. Before and after have the same values and input layouts.

The main comparison covers 25 operations/pipelines: 1,000-row contiguous input plus 1,000,000-row contiguous/fragmented/nullable input in eager and lazy modes (200 cases), and 25,000,000-row contiguous/fragmented input in lazy mode (50 cases). Each case has two warmups and five timed executions. A separate sweep covers 14 affected kernels at 2,048, 4,095, 4,096, 8,192, 131,072, 262,143, 262,144, and 524,288 rows, in eager and lazy modes (224 cases; three warmups and seven measurements). **All 474 paired cases match schemas, result fingerprints, and input chunk layouts.**

Selected 25-million-row lazy medians, in milliseconds:

#### Contiguous input

| Operation | Before (ms) | After (ms) | Speedup |
| --- | ---: | ---: | ---: |
| `cell_to_parent` | 94.59 | 13.55 | 6.98× |
| `cell_to_parent_string` | 1,386.68 | 94.54 | 14.67× |
| `cell_to_center_child` | 99.58 | 14.29 | 6.97× |
| `cell_to_children_size` | 104.12 | 14.63 | 7.12× |
| `latlng_to_cell_string` | 515.74 | 514.86 | 1.00× |
| `int_to_str` | 92.95 | 62.62 | 1.48× |
| `get_directed_edge_origin` | 120.06 | 13.72 | 8.75× |
| `get_directed_edge_destination` | 118.23 | 27.56 | 4.29× |
| `are_neighbor_cells` | 160.78 | 26.61 | 6.04× |
| `cells_to_directed_edge` | 162.92 | 35.82 | 4.55× |
| `cell_to_vertex` | 95.83 | 21.28 | 4.50× |
| `is_valid_vertex` | 101.86 | 22.76 | 4.48× |
| `child_pos_to_cell` | 172.71 | 25.96 | 6.65× |
| `grid_distance` | 294.87 | 210.07 | 1.40× |

#### Input split into 256 chunks

| Operation | Before (ms) | After (ms) | Speedup |
| --- | ---: | ---: | ---: |
| `cell_to_parent` | 9.18 | 10.25 | 0.90× |
| `cell_to_parent_string` | 116.75 | 85.92 | 1.36× |
| `cell_to_center_child` | 9.79 | 10.73 | 0.91× |
| `cell_to_children_size` | 9.18 | 10.65 | 0.86× |
| `latlng_to_cell_string` | 535.93 | 547.76 | 0.98× |
| `int_to_str` | 97.59 | 59.67 | 1.64× |
| `get_directed_edge_origin` | 123.05 | 13.25 | 9.29× |
| `get_directed_edge_destination` | 121.47 | 22.82 | 5.32× |
| `are_neighbor_cells` | 166.63 | 22.32 | 7.46× |
| `cells_to_directed_edge` | 171.71 | 28.34 | 6.06× |
| `cell_to_vertex` | 92.81 | 17.18 | 5.40× |
| `is_valid_vertex` | 94.52 | 18.45 | 5.12× |
| `child_pos_to_cell` | 58.67 | 20.78 | 2.82× |
| `grid_distance` | 295.29 | 175.01 | 1.69× |

The previously regressing large contiguous hierarchy calls are now roughly 7× faster than the first-pass release. Scalar string-parent lookup is about 14.7× faster; its gain combines parallel execution and reduced formatting allocations. Coordinate-to-string throughput is essentially unchanged at 25M in this run, despite sharing the new formatter. H3 coordinate calculation remains a substantial part of that operation.

Wall-time improvement does not always mean reduced total CPU work. Contiguous parent lookup uses 94.57 → 115.61 ms of process CPU time while its wall time falls to 13.55 ms. Integer-to-string conversion reduces process CPU time from 1,118.02 → 786.01 ms; edge-origin lookup from 317.18 → 139.26 ms. These are summed CPU times across threads. Contiguous edge-origin output drops from about 12,789 chunks to 16. Cheap fragmented kernels retain 256 chunks; expensive fragmented kernels produce 4,096 at this input size.

Whole-process peak RSS in the small/million-row matrix falls from 0.61 → 0.44 GiB. At 25M it is essentially unchanged, 4.60 → 4.59 GiB. These figures include setup, extra benchmark input columns, every case, and allocator retention; they are not isolated kernel allocation measurements and should not be compared directly with the earlier four-column dataset's memory totals.

### Rechecks and retained tradeoffs

Separate-process timing showed some substantial variation, including in unchanged controls. To check those results, `benchmarks/kernel_interleaved_profile.py` loads both preserved plugins in one process, prepares input once using the before build, constructs a query for each plugin, verifies schemas/fingerprints, and alternates before/after/after/before execution. Both libraries' thread pools exist in this diagnostic process, so it supplements rather than replaces the separate-process benchmarks. Setup, output hashing, and output disposal are outside timing.

For 25M fragmented input, seven alternating rounds produce 14 measurements per build after five warmups:

| Shared-input operation | Before (ms) | After (ms) | Change |
| --- | ---: | ---: | ---: |
| `get_resolution` | 6.556 | 6.477 | 1.2% faster |
| `is_valid_cell` | 6.258 | 6.099 | 2.6% faster |
| `cell_to_child_pos` | 17.440 | 18.152 | 4.1% slower |
| `cell_to_parent` | 8.846 | 9.030 | 2.1% slower |
| `cell_to_center_child` | 9.734 | 9.555 | 1.8% faster |
| `cell_to_children_size` | 9.660 | 10.077 | 4.3% slower |

The cheap hierarchy calls are 10–16% slower in the separate-process fragmented table, but the controlled comparison puts parent and children-count within 0.5 ms of the previous release, with center-child slightly faster. This is a retained small-call tradeoff, not a claim that every workload improves. The apparent large child-position regression in exploratory separate-process runs did not persist at that magnitude with shared input; the final shared-input difference is about 0.7 ms (4%).

Immediately below the new parallel threshold (262,143 contiguous rows), the same alternating method gives:

| Operation at 262,143 rows | Before (ms) | After (ms) | Change |
| --- | ---: | ---: | ---: |
| `cell_to_parent` | 0.899 | 0.969 | 7.8% slower |
| `cell_to_center_child` | 0.965 | 1.015 | 5.2% slower |
| `cell_to_children_size` | 0.987 | 1.026 | 4.0% slower |
| `int_to_str` | 1.374 | 0.953 | 30.6% faster |

Those hierarchy costs are approximately 0.04–0.07 ms (4–8%). The earlier 4,095-row coordinate-indexing tradeoff remains unchanged. A slower 8,192-row integer-to-string sweep result was checked separately with 15 alternating rounds: 0.233 → 0.217 ms (30 measurements per build), so its apparent slowdown was not stable. The implementation favors the substantial large-call improvements while documenting these smaller serial-path costs.

### Native CPU profiles and validation

Native `sample` profiles cover five seconds at a 1 ms interval while a task-owned process repeats `int_to_str` on fragmented million-row input. Both profiles use the corresponding final binary hash and are separate from timed benchmarks. Before stacks show temporary String growth/allocation and deallocation beneath string formatting and Arrow collection. After stacks show `HexStringBuilder::append`, formatting into the reusable String, and copying into Arrow's output buffer. These observations are consistent with the allocation change; stack counts and sampled loop counts are not treated as speedup measurements or CPU percentages. Output buffers and per-builder storage still allocate.

`make fmt`, `make lint`, `make install`, and all 337 tests passed during development. The final release was rebuilt with `make install-release`, and all 337 tests passed against it. The 31 new cases cover mixed integer/string pairs, mismatched chunks, nonzero slices, independent nulls, malformed hexadecimal input, negative/maximal indexes, pentagons, empty input, threshold boundaries, and shared list formatting. The installed extension is byte-identical to the final saved optimized binary. No dependencies or public API signatures changed.

### Reproduce and artifacts

All second-pass artifacts are under `/tmp/polars-h3-kernel-pass2/`. `before.json`/`after.json`, `before-25m.json`/`after-25m.json`, and `before-sweep.json`/`after-sweep.json` are the final paired matrices. `interleaved-recheck.json`, `interleaved-threshold.json`, and `interleaved-string-small.json` are the final shared-input diagnostics. `baseline-int_to_str-sample.txt` and `optimized-int_to_str-sample.txt` contain native stacks; matching `*-workload.json` files record hashes. Files labeled `candidate1`, `candidate2`, or `exploratory` describe intermediate builds/results and are not final measurements.

Run each matrix separately for `baseline.so` and `optimized.so`, changing its output filename:

    UV_CACHE_DIR=/tmp/polars-h3-uv-cache UV_OFFLINE=true POLARS_MAX_THREADS=16 RAYON_NUM_THREADS=16 uv run --no-sync -m benchmarks.kernel_profile --plugin /tmp/polars-h3-kernel-pass2/baseline.so --extended --rows 1000 1000000 --iterations 5 --warmups 2 --output /tmp/polars-h3-kernel-pass2/before.json

For 25M, replace the matrix arguments with `--extended --rows 25000000 --layouts contiguous fragmented --modes lazy --iterations 5 --warmups 2`. For the size sweep, use:

    --rows 2048 4095 4096 8192 131072 262143 262144 524288 --layouts contiguous --modes eager lazy --functions cell_to_parent cell_to_parent_string cell_to_center_child cell_to_children_size get_directed_edge_origin get_directed_edge_destination are_neighbor_cells cells_to_directed_edge cell_to_vertex is_valid_vertex child_pos_to_cell grid_distance int_to_str latlng_to_cell_string --iterations 7 --warmups 3

Reproduce the alternating shared-input check:

    UV_CACHE_DIR=/tmp/polars-h3-uv-cache UV_OFFLINE=true POLARS_MAX_THREADS=16 RAYON_NUM_THREADS=16 uv run --no-sync -m benchmarks.kernel_interleaved_profile --before /tmp/polars-h3-kernel-pass2/baseline.so --after /tmp/polars-h3-kernel-pass2/optimized.so --output /tmp/polars-h3-kernel-pass2/interleaved-recheck.json

For the threshold check, add `--rows 262143 --layout contiguous --functions cell_to_parent cell_to_center_child cell_to_children_size int_to_str` and a distinct output name. For the small formatter check, use `--rows 8192 --layout contiguous --functions int_to_str --rounds 15`. Native sampling uses the existing `--repeat int_to_str --rows 1000000 --layouts fragmented --modes lazy --duration 30 --ready-file ...` procedure described above, with the second-pass plugin paths.

Second-pass binary SHA-256 values:

    before: b3ea8cc4cc8ec47f6c1a9b52f92aa1424c5d0b4c5bce2b7420313333673fe4c0
    after:  3d17a2775ca2bba06cf8436e9ee22d513f0fc055da7df67a81e193fd76b1b5c9

## DuckDB comparison after both optimization passes

This comparison measures the installed final polars-h3 release against **DuckDB 1.5.5, community H3 extension v1.5.5, H3 core 4.5.0**. The Rust implementation uses **h3o 0.11.0** from Cargo.lock. It runs on the same machine and Python/Polars versions recorded above, with Polars, Rayon, and DuckDB each configured for 16 threads.

### Scope and interpretation

Both sides process the same deterministic **25-million-row valid dataset** and return only equivalent, fully materialized Polars output columns. The Polars input is contiguous. DuckDB is measured in two configurations: reading a registered Arrow table derived from that input, and reading a native DuckDB table loaded before timing. Data generation, Arrow registration, native-table loading, query construction, validation, and result disposal are excluded; query execution and conversion of DuckDB results to Polars are included. Thus this is a comparison for a Polars-result workflow, not isolated H3 function latency or every possible DuckDB workload.

Each main result is a median of five executions after two warmups. Engine order rotates between measurements; engines do not execute concurrently. All 25 operations pass full row-by-row validation for all three execution paths. Integer output widths are normalized outside timing; latitude/longitude outputs use an absolute tolerance of 1e-9 degrees and relative tolerance of 1e-12. The dataset contains valid cells and neighboring pairs, so this does not establish identical invalid-input semantics or arbitrary-distance performance.

**Against native DuckDB input, polars-h3 is about 1.2–1.8× faster on several hierarchy/coordinate operations and 4.5–4.9× faster on scalar string conversion/parent lookup. DuckDB is substantially faster on the cheap inspection operations.** Seven of the 25 cases differ by less than 10%. The unweighted median DuckDB/polars-h3 ratio is **1.05×**, which is best interpreted as roughly tied across this particular selection, not a universal overall-throughput score. The indexing → parent + resolution pipeline is 420 → 558 ms in polars-h3/DuckDB order, a 1.33× polars-h3 advantage.

### Main results

All times are milliseconds. A native ratio above 1 favors polars-h3; below 1 favors DuckDB. The single-chunk Arrow column is provided for transparency and must not be treated as general DuckDB performance.

| Operation | polars-h3 | DuckDB native | Native ratio | DuckDB single-chunk Arrow |
| --- | ---: | ---: | ---: | ---: |
| `get_resolution` | 73.63 | 9.20 | 0.12× | 79.78 |
| `get_resolution_string` | 263.46 | 165.39 | 0.63× | 2,120.05 |
| `is_valid_cell` | 63.20 | 12.09 | 0.19× | 120.25 |
| `is_pentagon` | 65.40 | 13.05 | 0.20× | 139.02 |
| `is_res_class_III` | 61.68 | 9.23 | 0.15× | 91.49 |
| `cell_to_parent` | 11.17 | 15.10 | 1.35× | 151.69 |
| `cell_to_parent_string` | 84.11 | 413.12 | 4.91× | 4,748.85 |
| `cell_to_center_child` | 11.52 | 14.22 | 1.23× | 135.72 |
| `cell_to_children_size` | 11.93 | 16.74 | 1.40× | 171.47 |
| `cell_to_child_pos` | 18.06 | 26.28 | 1.45× | 290.78 |
| `latlng_to_cell` | 403.09 | 549.65 | 1.36× | 7,058.97 |
| `latlng_to_cell_string` | 451.85 | 794.01 | 1.76× | 9,775.20 |
| `cell_to_lat` | 215.07 | 214.78 | 1.00× | 2,740.84 |
| `cell_to_lng` | 216.51 | 219.97 | 1.02× | 2,757.86 |
| `cell_to_latlng` | 233.31 | 280.59 | 1.20× | 3,033.97 |
| `int_to_str` | 58.04 | 263.00 | 4.53× | 2,586.41 |
| `get_directed_edge_origin` | 14.36 | 11.57 | 0.81× | 96.15 |
| `get_directed_edge_destination` | 21.22 | 21.69 | 1.02× | 226.27 |
| `are_neighbor_cells` | 22.39 | 20.80 | 0.93× | 217.83 |
| `cells_to_directed_edge` | 29.12 | 29.38 | 1.01× | 328.50 |
| `cell_to_vertex` | 16.18 | 20.83 | 1.29× | 228.02 |
| `is_valid_vertex` | 18.28 | 17.17 | 0.94× | 189.97 |
| `child_pos_to_cell` | 20.11 | 27.66 | 1.37× | 294.62 |
| `grid_distance` | 162.13 | 169.67 | 1.05× | 2,022.06 |
| `index_parent_resolution` | 420.00 | 558.24 | 1.33× | 7,232.03 |

The inspection results identify a remaining implementation gap on large contiguous input: `get_resolution`, `is_valid_cell`, `is_pentagon`, and `is_res_class_III` currently process each plugin call serially. DuckDB's native input can spread work across workers. These numbers are specific to contiguous Polars input; fragmented Polars inputs can be scheduled differently, as the earlier internal measurements demonstrate. No additional library optimization was performed for this comparison.

### Arrow batching check

The single-chunk Arrow path shows much lower effective parallel utilization. For coordinate indexing, its process CPU/wall-time ratio is about 2, versus about 14.7 for native DuckDB in this run. To test the impact of layout, a second run splits only the Arrow representation into 250 batches of 100,000 rows, outside timing. Polars keeps its contiguous input; native DuckDB remains a separately preloaded table. These three cases use one warmup and three timed runs and pass the same full value checks:

| Operation | polars-h3 (ms) | DuckDB batched Arrow (ms) | DuckDB native (ms) |
| --- | ---: | ---: | ---: |
| `cell_to_parent_string` | 78.80 | 453.99 | 443.31 |
| `latlng_to_cell` | 397.79 | 538.40 | 546.30 |
| `int_to_str` | 61.20 | 310.90 | 313.82 |

Batched Arrow largely closes the gap with native DuckDB. In particular, DuckDB coordinate indexing falls from about 7.1 s with a single Arrow chunk to 0.54 s with batched Arrow. Advertising the single-chunk Arrow ratios as a blanket library speedup would therefore be misleading. The native-input comparison is the primary result. These are not pure compute-only timings: DuckDB output conversion to Polars remains included in both configurations.

### Reproduce and validation

The new `benchmarks/duckdb_kernel_profile.py` driver loads the already-installed H3 extension without installing or updating dependencies. Raw timings, schemas, normalized result fingerprints, SQL expressions, versions, and the polars-h3 binary hash are saved under `/tmp/polars-h3-duckdb-profile/` in `results-25m.json` and `batched-arrow-25m.json`; `smoke.json` records the initial 1,000-row binding/value check. Floating-point fingerprints need not be identical even when the tolerance-based full comparison passes.

    UV_CACHE_DIR=/tmp/polars-h3-uv-cache UV_OFFLINE=true POLARS_MAX_THREADS=16 RAYON_NUM_THREADS=16 uv run --no-sync -m benchmarks.duckdb_kernel_profile --rows 25000000 --iterations 5 --warmups 2 --output /tmp/polars-h3-duckdb-profile/results-25m.json

    UV_CACHE_DIR=/tmp/polars-h3-uv-cache UV_OFFLINE=true POLARS_MAX_THREADS=16 RAYON_NUM_THREADS=16 uv run --no-sync -m benchmarks.duckdb_kernel_profile --rows 25000000 --iterations 3 --warmups 1 --arrow-batch-rows 100000 --functions cell_to_parent_string latlng_to_cell int_to_str --output /tmp/polars-h3-duckdb-profile/batched-arrow-25m.json

The final release binary is unchanged from the second optimization pass (SHA-256 3d17a2775ca2bba06cf8436e9ee22d513f0fc055da7df67a81e193fd76b1b5c9). Formatting, lint, and all 337 tests pass for the benchmark additions; both the smoke comparison and full-size comparisons validate their outputs directly. These measurements do not cover list expansion, boundary WKT, polygon coverage, or disk-backed/out-of-core workloads.
