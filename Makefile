.PHONY: help sync install install-release fmt lint test check docs bench clean

help:
	@echo "Targets:"
	@echo "  sync             Install dev dependencies"
	@echo "  install          Build/install extension in dev mode"
	@echo "  install-release  Build/install optimized extension"
	@echo "  fmt              Format Rust and Python"
	@echo "  lint             Run Rust/Python checks"
	@echo "  test             Run Python tests"
	@echo "  check            Run fmt, lint, install, and test"
	@echo "  docs             Serve docs locally"
	@echo "  bench            Run benchmarks after release build"
	@echo "  clean            Remove build artifacts"

sync:
	uv sync --all-groups

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
	uv run mypy polars_h3

test:
	uv run pytest tests

check: fmt lint install test

docs:
	uv run mkdocs serve

bench: install-release
	uv run -m benchmarks.engine

clean:
	cargo clean
	rm -rf .pytest_cache .ruff_cache .mypy_cache
