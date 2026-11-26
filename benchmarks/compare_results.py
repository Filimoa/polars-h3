"""Compare matching head_to_head runs without averaging unlike workloads."""

import argparse
import json
from pathlib import Path


def compare(before: dict, after: dict, baseline_engine: str = "polars") -> list[dict]:
    for key in (
        "threads",
        "resolution",
        "radius",
        "layout",
        "null_every",
        "arrow_batch_rows",
    ):
        assert (
            before["metadata"]["settings"][key] == after["metadata"]["settings"][key]
        ), f"different {key}"
    for key in ("platform", "versions", "duckdb_h3", "h3_core", "rustc"):
        assert before["metadata"][key] == after["metadata"][key], f"different {key}"
    old = {case["name"]: case for case in before["cases"]}
    rows = []
    for case in after["cases"]:
        if case["name"] not in old:
            continue
        baseline = old[case["name"]]
        assert baseline["rows"] == case["rows"], f"different rows for {case['name']}"
        assert baseline["sql"] == case["sql"], f"different work for {case['name']}"
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
            duckdb = current["duckdb", mode]
            rows.append(
                {
                    "name": case["name"],
                    "mode": mode,
                    "rows": case["rows"],
                    "before_seconds": previous["median_seconds"],
                    "after_seconds": result["median_seconds"],
                    "improvement": previous["median_seconds"]
                    / result["median_seconds"],
                    "duckdb_seconds": duckdb["median_seconds"],
                    "duckdb_over_polars": duckdb["median_seconds"]
                    / result["median_seconds"],
                    "ranges_overlap": not (
                        previous["min_seconds"] > result["max_seconds"]
                        or previous["max_seconds"] < result["min_seconds"]
                    ),
                }
            )
    assert rows, "no matching measurements"
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
        print(
            f"{row['name']:28} {row['mode']:12} {row['before_seconds']*1000:10.2f} {row['after_seconds']*1000:10.2f} {row['improvement']:6.2f}x {row['duckdb_over_polars']:7.2f}x {str(row['ranges_overlap']):>8}"
        )
    if args.output:
        args.output.write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
