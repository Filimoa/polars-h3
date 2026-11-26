.PHONY: help sync sync-bench install install-release fmt lint test check docs bench bench-h2h test-h3o test-sdist bench-h3o fuzz-h3o test-h3o-lab bench-h3o-lab fuzz-h3o-lab clean

FUZZ_TARGET ?= latltng_to_cell
FUZZ_SECONDS ?= 60

BENCH_OUTPUT ?= /tmp/polars-h3-head-to-head.json
BENCH_ARGS ?= --threads 8 --rows 5000000 --list-rows 250000 --polygon-rows 2000

help:
	@echo "Targets:"
	@echo "  sync             Install dev dependencies"
	@echo "  sync-bench       Install dev and benchmarking dependencies"
	@echo "  install          Build/install extension in dev mode"
	@echo "  install-release  Build/install optimized extension"
	@echo "  fmt              Format Rust and Python"
	@echo "  lint             Run Rust/Python checks"
	@echo "  test             Run Python tests"
	@echo "  test-h3o         Run vendored upstream tests"
	@echo "  test-h3o-lab     Compare vendored h3o with pristine crates.io h3o"
	@echo "  bench-h3o        Run upstream library benchmarks"
	@echo "  bench-h3o-lab    Compare global/Ohio core workloads with pristine h3o"
	@echo "  fuzz-h3o         Run upstream FUZZ_TARGET for FUZZ_SECONDS"
	@echo "  fuzz-h3o-lab     Fuzz exact compatibility with pristine h3o"
	@echo "  test-sdist       Build extracted sdist and verify licenses"
	@echo "  check            Run fmt, lint, install, and test"
	@echo "  docs             Serve docs locally"
	@echo "  bench            Build release and run validated DuckDB benchmarks"
	@echo "  bench-h2h        Build release and compare with DuckDB (BENCH_ARGS, BENCH_OUTPUT)"
	@echo "  clean            Remove build artifacts"

sync:
	uv sync --group dev

sync-bench:
	uv sync --group dev --group benchmarking

install:
	uv run maturin develop --uv

install-release:
	uv run maturin develop --release --uv

fmt:
	cargo fmt --package polars-h3
	uv run ruff format polars_h3 tests benchmarks scripts

lint:
	cargo clippy --all-features
	uv run ruff check polars_h3 tests benchmarks scripts
	uv run ty check polars_h3

test:
	uv run pytest tests

check: fmt lint test-h3o test-h3o-lab install test

docs:
	uv run --group docs zensical serve

bench: bench-h2h

bench-h2h: install-release
	UV_NO_SYNC=1 uv run --group benchmarking -m benchmarks duckdb $(BENCH_ARGS) --output "$(BENCH_OUTPUT)"

clean:
	cargo clean
	rm -rf .pytest_cache .ruff_cache

test-h3o:
	cargo test --manifest-path vendor/h3o/Cargo.toml --locked --all-features

test-sdist:
	uv run python scripts/check_sdist.py

bench-h3o:
	cargo bench --manifest-path vendor/h3o/Cargo.toml --locked --features geo --bench h3

fuzz-h3o:
	cd vendor/h3o && cargo +nightly fuzz run $(FUZZ_TARGET) -- -max_total_time=$(FUZZ_SECONDS)

test-h3o-lab:
	cargo test --manifest-path scripts/h3o-lab/Cargo.toml --locked --release

bench-h3o-lab:
	cargo bench --manifest-path scripts/h3o-lab/Cargo.toml --locked --bench core

fuzz-h3o-lab:
	cargo run --manifest-path scripts/h3o-lab/Cargo.toml --locked --release --bin seed-corpus
	cd scripts/h3o-lab && cargo +nightly fuzz run differential -- -max_total_time=$(FUZZ_SECONDS)
