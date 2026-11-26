"""Migration notice for the retired cold-run internal timer."""


def main():
    raise SystemExit(
        "benchmarks.large_engine has been retired. Use python -m benchmarks "
        "internal --rows N --output /tmp/new-results.json. Add "
        "--baseline-plugin PATH for exact before/after comparisons. "
        "All 46 operations are retained; run with --list or --help."
    )


if __name__ == "__main__":
    main()
