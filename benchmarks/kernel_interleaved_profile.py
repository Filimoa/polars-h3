"""Alternate preserved plugins on shared input to check process-state timing noise."""

import argparse
import hashlib
import json
import os
import platform
import statistics
import time
from pathlib import Path

import polars as pl

from benchmarks.kernel_profile import (
    extended_expressions,
    make_data,
    make_runner,
    prepare,
    use_plugin,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--after", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--rows", type=int, default=25_000_000)
    parser.add_argument(
        "--layout",
        choices=["contiguous", "fragmented", "nullable"],
        default="fragmented",
    )
    parser.add_argument(
        "--functions",
        nargs="+",
        default=[
            "get_resolution",
            "is_valid_cell",
            "cell_to_child_pos",
            "cell_to_parent",
            "cell_to_center_child",
            "cell_to_children_size",
        ],
    )
    parser.add_argument("--rounds", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=5)
    args = parser.parse_args()
    plugins = {"before": args.before.resolve(), "after": args.after.resolve()}
    use_plugin(plugins["before"])
    frame = prepare(
        make_data(args.rows, bool(set(args.functions) & extended_expressions().keys())),
        args.layout,
    )
    results = []
    for name in args.functions:
        runners = {}
        for label, path in plugins.items():
            use_plugin(path)
            runners[label] = make_runner(frame, name, "lazy")
        signatures = []
        for run in runners.values():
            out = run()
            signatures.append(
                {
                    "schema": {k: str(v) for k, v in out.schema.items()},
                    "fingerprint": out.hash_rows(seed=0).sum(),
                    "rows": out.height,
                }
            )
            del out
            for _ in range(args.warmups):
                run()
        assert signatures[0] == signatures[1], (name, signatures)
        times = {label: [] for label in runners}
        cpu_times = {label: [] for label in runners}
        for _ in range(args.rounds):
            for label in ["before", "after", "after", "before"]:
                cpu_start = time.process_time()
                start = time.perf_counter()
                out = runners[label]()
                times[label].append((time.perf_counter() - start) * 1000)
                cpu_times[label].append((time.process_time() - cpu_start) * 1000)
                del out
        item = {
            "name": name,
            "runs_ms": times,
            "cpu_runs_ms": cpu_times,
            "median_ms": {k: statistics.median(v) for k, v in times.items()},
            **signatures[0],
        }
        results.append(item)
        print(name, item["median_ms"], flush=True)
    report = {
        "metadata": {
            "plugins": {
                k: {
                    "path": str(v),
                    "sha256": hashlib.sha256(v.read_bytes()).hexdigest(),
                }
                for k, v in plugins.items()
            },
            "platform": platform.platform(),
            "python": platform.python_version(),
            "polars": pl.__version__,
            "polars_threads": pl.thread_pool_size(),
            "rayon_threads": os.environ.get("RAYON_NUM_THREADS", "default"),
            "rows": args.rows,
            "layout": args.layout,
            "mode": "lazy",
            "input_chunks": frame.n_chunks(strategy="all"),
            "rounds": args.rounds,
            "warmups": args.warmups,
            "order": ["before", "after", "after", "before"],
        },
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
