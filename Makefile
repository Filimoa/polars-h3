SHELL=/bin/bash
PYTHON = python
VENV_DIR = .venv
PIP = $(VENV_DIR)/bin/pip

.venv:
	$(PYTHON) -m venv $(VENV_DIR)
	$(PIP) install -U pip setuptools wheel
	$(PIP) install maturin polars ruff mypy pytest

install:
	unset CONDA_PREFIX && \
	source .venv/bin/activate && maturin develop

install-release:
	unset CONDA_PREFIX && \
	source .venv/bin/activate && maturin develop --release

pre-commit:
	cargo +nightly fmt --all && cargo clippy --all-features
	.venv/bin/python -m ruff format polars_h3 tests

test:
	.venv/bin/python -m pytest tests

run: install
	source .venv/bin/activate && python run.py

run-release: install-release
	source .venv/bin/activate && python run.py

