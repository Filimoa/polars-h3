"""One entry point for benchmarks; suite imports happen after CLI dispatch."""

import argparse
import importlib
import sys

SUITES = {
    "duckdb": "head_to_head",
    "internal": "regression",
    "python": "python_api",
    "baselines": "baselines",
    "compare": "compare_results",
}


def main():
    parser = argparse.ArgumentParser(
        description="Validated H3 benchmarks: DuckDB, broad internal, Python callbacks, bounded Python/pandas baselines, or saved-result comparison."
    )
    parser.add_argument("suite", choices=SUITES)
    # Parse only the suite so each runner owns --help and its arguments.
    args = parser.parse_args(sys.argv[1:2])
    sys.argv = [f"{sys.argv[0]} {args.suite}", *sys.argv[2:]]
    importlib.import_module(f"benchmarks.{SUITES[args.suite]}").main()


if __name__ == "__main__":
    main()
