# Optimize large datasets with a fair DuckDB H3 comparison

This living ExecPlan follows PLANS.md. Work from /Users/sergey/Developer/personal-projects/h3_polars.

The completed campaign below originally included a vendored dependency. The
user subsequently deferred that work to `experiment/h3o-core`; `perf/large-data`
uses crates.io h3o 0.11.0 with identical production sources. See
docs/dependency-separation-plan.md for the current branch/build validation.
Vendoring-specific commands and paths below describe the historical campaign
and are available on the experimental branch.

## Purpose / Big Picture

Make polars-h3 faster on large datasets with measured, correctness-preserving changes. Provide reproducible before/after and DuckDB comparisons that distinguish native computation/materialization from Arrow interchange. Keep the benchmark and validation workflow inside this repository. Preserve the preceding vendoring work, documented in docs/vendor-h3o-execplan.md. Public Python signatures and mathematical algorithms remain unchanged; benchmark commands and internal Rust execution change.

## Progress

- [x] (2026-11-25) Uploaded all nine raw JSON results with checksums to PR #28 and verified the downloaded ZIP and each original file byte-for-byte. Linked the archive from the report and ignored future raw dumps. Benchmark code and readable results remain versioned; no public API or build changes.
- [x] (2026-11-25) Prepared the cleaned PR branch: all nine archive filenames are referenced, numeric report tables and runtime/test sources are unchanged, and raw JSON is absent from the final tree.

- [x] (2026-11-25) Captured an immutable original release binary and source archive before modifying Rust kernels.
- [x] (2026-11-25) Added the 33-case head-to-head driver, paired-result comparison, four timing contracts, and make bench-h2h.
- [x] (2026-11-25) Optimized scalar validation, string formatting, binary operations, coordinate indexing and list buffers in two measured passes.
- [x] (2026-11-25) Added an exact 46-operation regression driver. It exposed a 100K-row scheduling regression; balanced batch counts fixed it. All 46 final comparisons pass, including dtypes and list order.
- [x] (2026-11-25) Final source passes formatting, Clippy, Ruff, typing, 413 Python tests, 1,132 upstream tests and an extracted-sdist build/license check. The release extension was rebuilt and tested from Python.
- [x] (2026-11-25) Final binary passed the complete 33-case 5M-row matrix at eight threads and 13 representative single-thread cases, in native and materialize-then-Arrow modes.
- [x] (2026-11-25) Final 25M-row, nullable/chunked/sliced and four-mode transfer runs passed. Preserved seven complete raw artifacts with verified binary hashes and finalized benchmarks/results/2026-11-25-large-data.md.

## Context and Orientation

Cargo.toml builds a Polars plugin using crates.io h3o 0.11.0. Python wrappers under polars_h3/core construct expressions; src/engine contains Rust operation modules. The original campaign used an identical vendored source snapshot, now preserved on experiment/h3o-core with its tests, fuzz targets and datasets. Its two inherited differential fuzz findings remain documented in that branch's vendor/h3o/UPSTREAM.md; this performance work does not change that numerical implementation.

benchmarks/head_to_head.py generates deterministic Ohio inputs, preloads native DuckDB tables, constructs original/current expressions pointing at saved plugin binaries, and validates every result after every timed run. Native materialization includes allocation/storage but excludes output export. Arrow materialization includes execution and export; DuckDB uses CTAS then SELECT/export to permit parallel H3 evaluation. Direct Arrow output and registered Arrow scans are separate optional contracts. Setup costs are reported independently. Identity cases reveal representation costs and never count as H3 wins.

benchmarks/compare_results.py compares matched settings and samples. benchmarks/regression.py uses all 46 cases from benchmarks/large_engine.py with exact original/current equality. benchmarks/engine.py remains the legacy Python-inclusive comparison, but its inequivalent DuckDB WKT boundary comparison has been removed. benchmarks/README.md explains commands and contracts; benchmarks/results/2026-11-25-large-data.md is the final report destination.

## Milestones and Plan of Work

The first milestone established release provenance and a fair benchmark. Both engines use identical logical inputs, matched thread counts, two excluded warmups and five measured samples in rotating order. Metadata includes actual binary hashes, versions, SQL, wall/CPU samples, input/output sizes and chunks. Large scalar inputs use five million rows; list expansion uses 250K and polygons 2K. Selected scalar workloads also use 25M rows. Validation normalizes integer widths, unordered list order and documented float tolerances only; the separate original/current driver compares exact values and ordering.

The second milestone removed redundant whole-column parsing vectors, per-row allocations and highly fragmented output. src/engine/utils.rs supplies fused index mapping, bounded binary parsing, direct list builders, amortized hex formatting, and balanced parallel chunks capped at 65,536 rows. Consumers are indexing.rs, inspection.rs, hierarchy.rs, edge.rs, metrics.rs, traversal.rs and vertexes.rs. Disk scratch is reused and cleared before safe fallback; existing null, invalid, dtype and ring behavior remains intact.

The final milestone runs the complete matrix with the final immutable release, preserves raw samples, documents gains and limitations, and checks packaging and Python behavior. All checks must be complete before declaring success. No aggregation of unlike workloads or claim of universal DuckDB superiority is allowed.

## Concrete Steps

Use uv and Make. The final source was checked with:

    UV_NO_SYNC=1 make fmt lint install test
    UV_NO_SYNC=1 make install-release
    UV_NO_SYNC=1 make test
    UV_NO_SYNC=1 make test-h3o
    UV_NO_SYNC=1 make test-sdist

For a fresh comparison after make sync-bench:

    make bench-h2h BENCH_OUTPUT=/tmp/h3-new-run.json

For paired checks, save the original release plugin and run:

    UV_NO_SYNC=1 uv run -m benchmarks.head_to_head --threads 8 --rows 5000000 --list-rows 250000 --polygon-rows 2000 --iterations 5 --warmups 2 --baseline-plugin /tmp/polars-h3-large-optimization/baseline.abi3.so --plugin-path /tmp/polars-h3-large-optimization/candidate3.abi3.so --output /tmp/h3-new-run.json
    UV_NO_SYNC=1 uv run -m benchmarks.compare_results /tmp/h3-new-run.json /tmp/h3-new-run.json --baseline-engine baseline
    UV_NO_SYNC=1 uv run -m benchmarks.regression --baseline-plugin /tmp/polars-h3-large-optimization/baseline.abi3.so --plugin-path /tmp/polars-h3-large-optimization/candidate3.abi3.so --rows 100000 --threads 8 --output /tmp/h3-regression-new.json

The final matrix script /tmp/polars-h3-large-optimization/run-final-matrix.sh completed successfully, sequentially and without competing builds. Its final-main-8t.json (33 cases), final-single-thread.json (13), final-large-25m.json (6), final-chunked-null.json (7), final-sliced-null.json (7), final-transfer.json (4), and final-regression.json (46) were copied to dated files under benchmarks/results. Case/sample counts and final binary hashes were verified before report generation. No benchmark process remains active. New runs must use new output paths; the driver refuses overwrites.

## Validation and Acceptance

All main and variant results must match, with full values checked outside timing for every sample. The exact 46-case driver must preserve dtype and list order. tests/test_large_batches.py covers independently chunked arrays, sliced/null offsets, UInt64/Int64/String cells, Float32/Float64 coordinates, invalid values, pentagon fallback and global points at resolutions 0, 1, 5, 9 and 15. tests/test_benchmark_contracts.py verifies mismatch detection and deterministic input layouts.

The final report must include native and Arrow contracts, single-thread and large-input results, unchanged/noisy paths, thread/version/hardware details and source/binary provenance. Byte counts are buffer estimates, not peak RSS. Geographic and cross-library null differences must be disclosed. Required build, lint, Python, upstream and packaging checks must pass. CI configuration is not evidence of a remote run; only local checks executed here may be claimed.

## Surprises & Discoveries

Original per-row Rayon collectors produced thousands of output chunks, and several kernels parsed whole columns serially before parallel work. Bounded fused processing removed those bottlenecks. String parent lookup improved by roughly an order of magnitude in intermediate eight-thread measurements.

Initial exploratory benchmarks inherited fragmentation from setup expressions. Input generation now explicitly rechunks before applying the chosen layout, with a regression test. Those stopped runs are diagnostic only. Unordered-list and floating-coordinate validation also needed efficient full-value comparisons to avoid per-inner-list dispatch overhead; no validation was sampled or weakened.

DuckDB direct SELECT/Arrow fetching used much less CPU parallelism than native CTAS. The final report includes separate contracts and CPU/wall ratios so this is not mislabeled as copying cost or H3 kernel superiority.

The 100K-row exact regression run exposed a 19% area-calculation regression in candidate 2: a 16K minimum produced only seven tasks on eight workers. Candidate 3 rounds batch counts to worker multiples at both size bounds. In the final broad run, area improves from 6.55 to 5.96 ms, edge length from 3.89 to 3.23 ms, and vertex lists from 10.41 to 8.36 ms. Small differences in unchanged operations have overlapping sample ranges.

Overlapping Maturin builds emitted a shared staging-file restoration warning. Packaging was repeated in isolation and passed cleanly. The installed plugin, saved candidate and target/release library were verified byte-identical; subsequent measurements use the immutable saved binary.

## Decision Log

2026-11-25 / Codex: Store raw benchmark runs in a checksummed PR attachment and keep reports, runners and tests in Git. The nine generated files contributed 24,626 lines without serving as automated baselines. Verified the downloaded archive before removing repository copies.

2026-11-25 / Codex: Preserve vendored h3o's numerical algorithms and focus on measured integration overhead. The user authorized aggressive optimization, but correctness and real before/after evidence remain acceptance requirements.

2026-11-25 / Codex: Interleave saved original/current libraries and DuckDB in one process on the same input, with matched threads, to reduce drift. Use actual Polars plugin-path resolution because the package directory contains a stale second extension file.

2026-11-25 / Codex: Compare native and common-output paths separately. Exclude inequivalent boundary representations and identity cases from H3 performance claims. Preserve every raw sample and include limitations.

2026-11-25 / Codex: Add a broad exact regression driver and fix the medium-size scheduling regression it exposed before final measurements. Round task counts to worker multiples rather than accepting a large-input-only improvement.

## Outcomes & Retrospective

Completed. The final report is in benchmarks/results; all nine raw JSON artifacts (the original seven plus two registry checks) are preserved in the verified PR attachment linked from its Raw data section. At 25M rows/eight threads, native string-parent lookup improves 11.63x, string parsing 8.62x, parent lookup 7.20x, and coordinate indexing 1.23x against the original. The complete eight-thread main matrix has lower optimized medians than DuckDB for all 31 matched H3 cases, in both reported timing contracts; the two identity controls are excluded. Single-thread results, output-transfer costs, sample ranges and workload limits are reported separately. All 46 broad comparisons preserve exact values, dtypes and list order. All required local checks passed, and the installed extension matches the measured release binary.

The most important finding is that integration overhead and batch scheduling offered substantial gains without modifying H3 numerical algorithms. Native DuckDB comparisons were necessary to avoid attributing its direct-Arrow execution behavior entirely to copying. The broad regression check prevented accepting a medium-size slowdown that the largest workloads had hidden. Known inherited fuzz discrepancies and unexecuted remote CI remain explicitly documented; they are not new regressions or hidden test exclusions.

## Idempotence and Recovery

Benchmark output paths refuse overwrites. Preserve baseline/candidate snapshots and use new output names for retries. The original source is src/ at commit 5200e0768d55c712bd1b99a9c22b4a25c7cf544b, built with the unchanged vendored dependency and same release profile. Restore only task-owned experimental edits if a regression requires reversal; do not discard the prior vendoring work. Avoid simultaneous Maturin builds because they share staging paths.

## Artifacts and Notes

All local logs and immutable binaries are under /tmp/polars-h3-large-optimization. baseline-src.tar.gz and baseline.abi3.so precede runtime edits. candidate1 and candidate2 results are intermediate evidence; only final-* files are the final matrix. The final runtime source snapshot is candidate3-src.tar.gz. Final plugin SHA-256 is caf3e6de9e3fbe0804b6f21de194a78e0bc952de4fb81884e4289f8a829cb5a8; baseline SHA-256 is 39f22c98c298396f15eb0e57787a844eaacdc00023cefb2130b01fda8bff393a.

Validation logs: candidate3-dev-checks.log, candidate3-release-build.log, final-python-tests.log, final-h3o-tests.log, and final-sdist-sequential.log. That campaign's installed extension matched candidate3.abi3.so. The registry-backed rebuild is documented in docs/dependency-separation-plan.md.

## Interfaces and Dependencies

No public Python API changes or new runtime dependencies. The benchmark uses installed Polars, PyArrow and DuckDB with H3. It loads an installed H3 extension by default; installation requires the explicit --install-extension flag. New repository commands are make bench-h2h and the Python benchmark modules. Upstream vendoring/build changes are detailed separately in docs/vendor-h3o-execplan.md.

Revision note (2026-11-25): Recorded the completed matrix, preserved artifacts, final checks and measured outcomes after the last audit.

Revision plan (2026-11-25): Package the nine dated JSON files with per-file SHA-256 checksums, upload the ZIP to PR #28, and download it to verify byte equality before removing Git copies. Update benchmarks/README.md, the report, and .gitignore. Accept when the downloaded archive matches every original file, report links resolve, and the final PR diff contains no raw JSON. No runtime changes or benchmark reruns are needed. The archive and original commit permit recovery.

Artifact-storage validation (2026-11-25): Downloaded ZIP SHA-256 is 670f4db6f8403a702983124957b3dd48062cce591b30115df55fc55990a36e8f. Python zipfile.testzip passed; all nine JSON members matched the original bytes and SHA256SUMS entries. This documentation/artifact-only follow-up does not require rerunning the unchanged Rust/Python tests.
