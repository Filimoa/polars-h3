.PHONY: help sync sync-bench install install-release fmt lint test check docs bench bench-h2h clean

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
	cargo fmt --all
	uv run ruff format polars_h3 tests benchmarks

lint:
	cargo clippy --all-features
	uv run ruff check polars_h3 tests benchmarks
	uv run ty check polars_h3

test:
	uv run pytest tests

check: fmt lint install test

docs:
	uv run --group docs zensical serve

bench: bench-h2h

bench-h2h: install-release
	UV_NO_SYNC=1 uv run --group benchmarking -m benchmarks duckdb $(BENCH_ARGS) --output "$(BENCH_OUTPUT)"

clean:
	cargo clean
	rm -rf .pytest_cache .ruff_cache
