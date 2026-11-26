"""Migration notice for the retired unvalidated cross-library runner."""


def main():
    raise SystemExit(
        "benchmarks.engine has been retired. Use python -m benchmarks duckdb "
        "for matched DuckDB comparisons, python -m benchmarks python for "
        "Python H3 callbacks, or python -m benchmarks internal for Polars-only "
        "timings. Run a suite with --help; see benchmarks/README.md."
    )


if __name__ == "__main__":
    main()
