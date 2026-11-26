"""Compare complete matching runs without averaging unlike workloads.

Also reads the original archived DuckDB reports (which predate status/schema fields).
"""

import argparse
import json
from pathlib import Path


def compare(before: dict, after: dict, baseline_engine: str = "polars") -> list[dict]:
    for report in (before, after):
        if report.get("status", "complete") != "complete":
            raise ValueError("cannot compare incomplete or failed benchmark runs")
    if before["metadata"].get("suite", "duckdb") != after["metadata"].get(
        "suite", "duckdb"
    ):
        raise ValueError("different benchmark suites")
    for key in (
        "iterations",
        "warmups",
        "threads",
        "resolution",
        "radius",
        "layout",
        "null_every",
        "arrow_batch_rows",
    ):
        if before["metadata"]["settings"].get(key) != after["metadata"]["settings"].get(
            key
        ):
            raise ValueError(f"different {key}")
    for key in (
        "platform",
        "processor",
        "logical_cpus",
        "versions",
        "duckdb_h3",
        "h3_core",
        "rustc",
        "polars_threads",
        "rayon_threads",
        "duckdb_threads",
    ):
        if before["metadata"].get(key) != after["metadata"].get(key):
            raise ValueError(f"different {key}")
    old = {case["name"]: case for case in before["cases"]}
    rows = []
    for case in after["cases"]:
        if case["name"] not in old:
            continue
        baseline = old[case["name"]]
        for key in ("rows", "sql", "input_schema"):
            if baseline.get(key) != case.get(key):
                raise ValueError(f"different {key} for {case['name']}")
        prior = {
            (result["engine"], result["mode"]): result for result in baseline["results"]
        }
        current = {
            (result["engine"], result["mode"]): result for result in case["results"]
        }
        for (engine, mode), result in current.items():
            if engine != "polars" or (baseline_engine, mode) not in prior:
                continue
            previous = prior[baseline_engine, mode]
            duckdb = current.get(("duckdb", mode))
            rows.append(
                {
                    "name": case["name"],
                    "mode": mode,
                    "rows": case["rows"],
                    "before_seconds": previous["median_seconds"],
                    "after_seconds": result["median_seconds"],
                    "improvement": previous["median_seconds"]
                    / result["median_seconds"],
                    "duckdb_seconds": duckdb["median_seconds"] if duckdb else None,
                    "duckdb_over_polars": duckdb["median_seconds"]
                    / result["median_seconds"]
                    if duckdb
                    else None,
                    "ranges_overlap": not (
                        previous["min_seconds"] > result["max_seconds"]
                        or previous["max_seconds"] < result["min_seconds"]
                    ),
                }
            )
    if not rows:
        raise ValueError("no matching measurements")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--baseline-engine", choices=["polars", "baseline"], default="polars"
    )
    args = parser.parse_args()
    rows = compare(
        json.loads(args.before.read_text()),
        json.loads(args.after.read_text()),
        args.baseline_engine,
    )
    print(
        f"{'operation':28} {'mode':12} {'before ms':>10} {'after ms':>10} {'gain':>7} {'Duck/PL':>8} {'overlap':>8}"
    )
    for row in rows:
        duckdb = (
            f"{row['duckdb_over_polars']:.2f}x"
            if row["duckdb_over_polars"] is not None
            else "—"
        )
        print(
            f"{row['name']:28} {row['mode']:12} {row['before_seconds']*1000:10.2f} {row['after_seconds']*1000:10.2f} {row['improvement']:6.2f}x {duckdb:>8} {str(row['ranges_overlap']):>8}"
        )
    if args.output:
        with args.output.open("x") as stream:
            stream.write(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
