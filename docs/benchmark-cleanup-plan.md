# Consolidate benchmark entry points and measurement contracts

This living ExecPlan follows PLANS.md. Work in /Users/sergey/Developer/personal-projects/h3_polars.

## Purpose / Big Picture

Make the validated large-data harness the normal benchmark workflow. Preserve the 33 DuckDB cases, 46 broad internal operations, and the old suite's Python comparison coverage while retiring its unvalidated timing loops. Provide one discoverable CLI, shared timing/provenance/result storage, and explicit suite-specific comparison contracts. Public package APIs and Rust execution do not change. Developer commands change: make bench selects the validated DuckDB suite; old module CLIs explain migration. No packaging or dependency changes are required in this pass. Update notebooks/benchmarking.ipynb to consume the shared report format; historical results remain in Git history and the published report/archive.

## Progress

- [x] (2026-11-25) Audited all five benchmark modules, Make targets, README instructions and existing contract tests.
- [x] (2026-11-25) Extracted shared measurement, provenance and result-storage utilities and workload definitions.
- [x] (2026-11-25) Replaced legacy timing loops with explicit DuckDB, internal and Python suites, keeping their distinct validation contracts.
- [x] (2026-11-25) Updated commands/docs and contract tests; real smoke runs pass the 33 DuckDB, 46 internal and 14 Python cases. Verified completed reports, sample counts, thread counts and the registry release hash.
- [x] (2026-11-25) Completed make fmt/lint/test: 424 tests pass. Reviewed the diff, checked Make dispatch, executed notebook cells against saved JSON, and verified legacy archived DuckDB reports still compare.

## Surprises & Discoveries

The head-to-head polygon generator imports the old engine, indirectly importing DuckDB and Python H3. The old engine installs DuckDB H3 unconditionally, compares outputs with different retained columns, and never validates equivalence. The broad standalone runner has no excluded warmups; the new regression runner depends on it for its valuable 46-case catalog. README documents an unregistered h3-bench command. Existing dated results remain historical measurements and must not be rewritten.

The shared-order test exposed that rotating then reversing two engines canceled out, always running the same one first. Two-engine trials now alternate explicitly; the original three-engine paired order is preserved. The benchmark notebook also used removed internal classes and an overall speedup aggregate; it now reads saved results with no independent timer. Removed the README's unsupported universal 25x/5x claims in favor of the measured per-operation report.

## Decision Log

2026-11-25 / Codex: Keep distinct DuckDB, broad internal, and Python comparison suites; share timing and evidence handling rather than pretending all engines have identical materialization semantics. Preserve the established DuckDB datasets/contracts and broad case definitions. Python comparison includes Python callback/Polars materialization overhead and uses explicit integer H3 APIs for matching representations. No universal speedup aggregate.

2026-11-25 / Codex: Use a separate cleanup commit on the existing performance branch. Keep runtime source untouched and retain old evidence/archive links. Legacy benchmark Python classes were internal tooling, not public polars_h3 APIs; replace their CLI entry points with migration instructions rather than silently reinterpret old flags.

## Context and Orientation

Before this cleanup, benchmarks/head_to_head.py combined DuckDB cases, datasets, validation, timing and CLI. benchmarks/large_engine.py contained the broad case catalog and an older timer; regression.py consumed that catalog. benchmarks/engine.py was the obsolete cross-library timer with useful Python coverage. tests/test_benchmark_contracts.py tests full-output validation and deterministic layouts. Makefile and README.md advertised competing defaults.

## Plan of Work

Extract common.py for lightweight CLI controls, plugin selection, timing, metadata and protected JSON reports; separate DuckDB and internal workloads from execution. Preserve existing head_to_head module as a supported historical CLI. Make the internal runner accept an optional saved baseline, with exact every-output comparisons and a clearly labeled repeatability check when no baseline is provided. Add a Python suite sharing DuckDB input generation and full-output comparison, including the legacy boundary/path cases. Add python -m benchmarks subcommands and list support. Retire engine.py and large_engine.py timing implementations with actionable migration errors. Update benchmark guide and top-level README.

## Concrete Steps and Validation

Run UV_NO_SYNC=1 make fmt lint test. Run fresh subprocess smoke benchmarks with threads set before importing Polars: all DuckDB cases on 128 scalar/32 list/2 polygon rows across four modes; all 46 internal cases on 128 rows, both current-only and saved-baseline; all Python cases on 128 rows. Use one excluded warmup and two measured samples. Save each JSON to a unique /tmp path. Validate report completion, counts, raw samples and plugin hashes. Exercise unknown functions, zero sizes and existing output rejection before expensive work. Verify the previous archived results remain readable by compare_results. Runtime remains unchanged, so no Rust rebuild is needed except the existing release binary is verified from Python.

## Validation and Acceptance

All suite outputs pass their documented full-value gates. Warmups never enter sample arrays; failures preserve an explicitly incomplete/failed artifact, and existing files cannot be overwritten. CLI help/listing and internal/Python execution do not require DuckDB imports. Each report records machine/version/thread/binary provenance and its timing contract. Existing archived benchmark numbers remain unchanged. Required repo checks pass.

## Idempotence and Recovery

Use new output paths; retain the original benchmark archive and saved binaries. Do not install extensions automatically. Keep input-generation changes out of the established DuckDB workloads so old evidence remains interpretable. Git retains the old runners if tooling migration needs review.

## Outcomes & Retrospective

Completed locally. One CLI dispatches three suites with shared sampling, plugin provenance and checkpointed JSON. The benchmark Python code shrank from 2,064 to 1,472 lines while retaining the 33 DuckDB cases, 46 internal operations and 14 Python cases. AST comparisons verify both extracted workload catalogs are unchanged. The legacy classes/timers are retired with migration messages; the notebook consumes saved results. Rust/package code and the dated performance report are unchanged.

Validation: UV_CACHE_DIR=/tmp/polars-h3-uv-cache UV_NO_SYNC=1 make fmt lint test passed (424 tests), logged in /tmp/h3-cleanup-final-checks.log. Completed smoke reports under /tmp/h3-cleanup-: duckdb-final (33 cases, four modes), three-engine-final (three cases, two modes, saved baseline), internal-final (46 current-only), internal-paired-1 (46 exact baseline), python-final (14). All use two threads, one excluded warmup and two recorded samples. Every report identifies registry plugin SHA-256 641f3d597e97866b0eeb4332e6bc870442e36951eb2821607189a7d5c31f38a5. These tiny runs verify behavior, not performance claims.

The comparison utility successfully read all seven historical DuckDB JSON files from the archived evidence bundle. Notebook code executed against the final DuckDB smoke report and produced 264 rows (case/mode/engine). No raw smoke artifacts were added to Git. The main improvement is a single tested measurement contract per scenario, including a regression test for the two-engine ordering bug.

Revision note (2026-11-25): Recorded final implementation, migration changes, smoke evidence and required checks. No dependency upgrades or runtime changes were introduced.
