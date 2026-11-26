# Separate performance improvements from h3o vendoring

This ExecPlan follows PLANS.md. Work in /Users/sergey/Developer/personal-projects/h3_polars.

## Purpose and scope

Keep the measured Polars integration optimizations on `perf/large-data`, using the unchanged crates.io h3o 0.11.0 dependency. Preserve vendored source, upstream tests/fuzzing, CI and packaging work on `experiment/h3o-core` for later core-library optimization. This restores Cargo dependency sourcing, Python build/license metadata and ordinary check targets on the performance branch; public Python APIs and optimized Rust kernels do not change. No core-library optimization or remote push is part of this step.

## Progress

- [x] (2026-11-25) Reviewed the worktree and identified vendor-only versus performance changes; shared Makefile changes need separation.
- [x] (2026-11-25) Preserved all source work in a backup and committed vendor-only changes as 3d0f997 on experiment/h3o-core.
- [x] (2026-11-25) Created perf/large-data, restored registry Cargo/packaging metadata and ordinary check targets, and relocated vendor-only files intact.
- [x] (2026-11-25) Rebuilt against crates.io: formatting/lint and 413 tests pass, all 46 exact comparisons pass, and eight paired workloads retain the gains. Preserved two additional raw artifacts and updated the performance report.
- [x] (2026-11-25) Committed performance-only changes, rebased experiment/h3o-core onto them, and audited both branches. The performance branch has no Cargo, packaging, licensing or vendoring delta from master; all 283 vendor files are preserved on the experimental branch.

## Plan of work

Back up modified/untracked source files (excluding ignored build outputs) and the original combined Makefile under /tmp/polars-h3-dependency-split. Create a temporary worktree at the original base with `experiment/h3o-core`, copy vendor-only files, remove performance targets from its Makefile, and commit those changes. Verify their contents before removing anything from the original worktree.

Create `perf/large-data` in the original worktree. Restore vendor-only tracked files from the original base, retain only benchmark additions in Makefile, and relocate the vendor directory and helper files to the backup so ignored build data is preserved too. Update documentation to describe the historical benchmark provenance and the deferred branch without broken links. Rebuild, test and record registry-dependency equivalence. Commit performance changes. Rebase the new local experimental commit onto the performance branch, resolving the shared Makefile by retaining both sets of targets.

## Validation and acceptance

Cargo metadata on the performance branch must resolve h3o 0.11.0 from crates.io. Verify its production sources match the preserved vendored sources. Run `UV_NO_SYNC=1 make fmt lint install test`, then `UV_NO_SYNC=1 make install-release` and test the release extension. Run the 46-operation exact comparison against the saved optimized vendored binary and a representative head-to-head run against the original baseline. Do not run builds or tests during performance measurements. Preserve the previous raw results as historical evidence; record the new registry build separately. Final Git diffs must contain no vendor or packaging changes on the performance branch; the experimental branch must retain all original vendor assets and tooling. Neither branch is pushed.

## Surprises and discoveries

The vendor directory includes about 1.2 GB of ignored build data. Copy only source files into the preservation commit, and relocate the original directory intact rather than deleting build outputs. Cargo metadata resolves registry h3o 0.11.0, and all 60 production source files match the preserved vendored tree byte-for-byte. Both registry-backed development and release builds pass all 413 tests; formatting and lint pass. All 46 operation comparisons against the optimized vendored binary preserve exact values, dtypes and list ordering. The performance gains do not depend on edits to h3o production source. Existing report metadata honestly records the earlier vendored build and must not be rewritten as a registry build.

## Decisions

2026-11-25 / Codex: Use two local branches with focused commits. First preserve vendoring durably, then clean the performance branch. Layer the experimental branch onto the final performance commit so future core work starts with the wrapper improvements. These local branch/commit operations implement the user's requested separation; they do not publish or merge anything remotely.

## Recovery and artifacts

Original base: 5200e0768d55c712bd1b99a9c22b4a25c7cf544b. Backup and validation logs: /tmp/polars-h3-dependency-split. Existing measured baseline and optimized binaries: /tmp/polars-h3-large-optimization/baseline.abi3.so and candidate3.abi3.so. Never overwrite them. If interrupted, inspect branch status and the preservation commit before continuing. Restore task-owned files from the backup only when needed; do not discard other changes.

## Outcomes

Completed. The current branch is perf/large-data, with the registry-backed release installed. experiment/h3o-core adds only the deferred vendoring, validation and packaging work on top. Both are local branches; master and remote refs remain unchanged. Formatting/lint, 413 Python tests and all 46 exact operation comparisons pass. Eight paired workloads retain the speedups against the original baseline, including approximately 11.1x string-parent lookup, 6.7x parent lookup and 1.23x coordinate indexing at five million rows/eight threads. Raw registry verification results and the updated report are in benchmarks/results. All vendor source files and the original ignored build data were preserved. The temporary worktree can be removed after the final history audit; branch commits retain the source.

Revision note (2026-11-25): Recorded successful registry verification and the completed local branch separation.
