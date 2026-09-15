# Contributor Guide

This guide gives contributors the minimum project context needed to work on `polars-h3`. Keep changes small, use the existing patterns, and verify the Rust extension from Python before calling work done.

## Project Structure

- `src/`: Rust implementation of the Polars plugin expressions.
- `src/engine/`: H3 operation modules grouped by feature area, such as indexing, traversal, metrics, hierarchy, edges, and inspection.
- `polars_h3/`: Python package and public user-facing wrappers.
- `polars_h3/core/`: Python functions that expose the Rust expressions through Polars.
- `tests/`: Python test suite for the public package behavior.
- `benchmarks/`: Benchmark helpers for comparing performance.
- `docs/`: MkDocs documentation source.
- `notebooks/`: Examples and exploratory notebooks.
- `Cargo.toml`, `Cargo.lock`: Rust package metadata and locked Rust dependencies.
- `pyproject.toml`, `uv.lock`: Python package metadata and locked Python dependencies.
- `Makefile`: Common local development commands.

## Development Workflow

Use `uv` for Python commands and `make` for common repo tasks.

```bash
make sync
make install
make test
```

Run `make install` after changing Rust code so the local Python environment uses the rebuilt extension.

For optimized builds and benchmarks:

```bash
make install-release
make bench
```

For docs:

```bash
make docs
```

## Checks

Before finishing code or build configuration changes, run the relevant checks:

```bash
make fmt
make lint
make test
```

For a broader local pass:

```bash
make check
```

`make check` formats, lints, rebuilds the extension in development mode, and runs the test suite.

## ExecPlans

Use an ExecPlan for work that is multi-step, spans several files, adds a feature, performs a refactor, or is likely to take more than about an hour. Small fixes and documentation-only updates do not need one.

When an ExecPlan is useful, create or update a plan using the rules in `PLANS.md`. The plan should be self-contained enough that another contributor can pick it up later, and it should stay current as work progresses.

At minimum, a plan should explain:

- What user-visible behavior or maintenance outcome the work should produce.
- Which files or modules are likely to change.
- The concrete commands used to validate the work.
- Progress, surprises, decisions, and final outcome.

If a change affects public Python APIs, documented behavior, package metadata, or release/build behavior, call that out in the plan before implementing the change.

## Coding Guidelines

- Prefer existing module boundaries. Add indexing behavior under `src/engine/indexing.rs` and `polars_h3/core/indexing.py`, traversal behavior under the traversal modules, and so on.
- Keep Rust expression names, Python wrapper names, and tests aligned by feature area.
- Add or update tests in `tests/` when behavior changes.
- Keep Python APIs simple and Polars-native. Public functions should accept column expressions or column names in the same style as the existing wrappers.
- Avoid unrelated refactors while changing feature code.
- Do not edit generated or build output such as `target/`, cache directories, or notebook checkpoint files.

## Pull Request Expectations

- Summarize what changed and why.
- Mention user-facing behavior changes.
- Include the checks you ran, especially `make test` or `make check`.
- Keep commits focused and use concise imperative commit messages.
