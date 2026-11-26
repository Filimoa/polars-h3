"""Paired broad-API regression check using immutable original/current plugins.

Unlike the DuckDB comparison, this checks exact output values, list ordering,
and dtypes. Setup and validation are excluded from timing.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import statistics
from pathlib import Path

from benchmarks.head_to_head import measure, positive, use_plugin


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-plugin", required=True, type=Path)
    parser.add_argument("--plugin-path", required=True, type=Path)
    parser.add_argument("--threads", default=8, type=positive)
    parser.add_argument("--rows", default=100_000, type=positive)
    parser.add_argument("--iterations", default=5, type=positive)
    parser.add_argument("--warmups", default=2, type=positive)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; choose a new path")
    for name in ("baseline_plugin", "plugin_path"):
        path = getattr(args, name).resolve()
        if not path.is_file():
            parser.error(f"missing binary: {path}")
        setattr(args, name, path)
    os.environ["POLARS_MAX_THREADS"] = str(args.threads)
    os.environ["RAYON_NUM_THREADS"] = str(args.threads)

    import polars as pl
    from polars.testing import assert_frame_equal

    from benchmarks.large_engine import cases, make_data, prepare_frame

    use_plugin(args.plugin_path)
    data = make_data(args.rows).rechunk()
    report = {
        "settings": {
            k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()
        },
        "polars_version": pl.__version__,
        "binary_sha256": hashlib.sha256(args.plugin_path.read_bytes()).hexdigest(),
        "baseline_binary_sha256": hashlib.sha256(
            args.baseline_plugin.read_bytes()
        ).hexdigest(),
        "validation": "exact values, dtypes and list ordering; every output",
        "cases": [],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for case in cases().values():
        frame = prepare_frame(data.head(min(args.rows, case.rows)), case.name).rechunk()
        exprs = {}
        for engine, path in (
            ("baseline", args.baseline_plugin),
            ("polars", args.plugin_path),
        ):
            use_plugin(path)
            exprs[engine] = case.expr().alias("result")
        reference = frame.select(exprs["baseline"])
        samples = {engine: [] for engine in exprs}
        for iteration in range(-args.warmups, args.iterations):
            order = list(exprs)
            if iteration % 2:
                order.reverse()
            for engine in order:
                gc.collect()
                output, timing = measure(
                    lambda frame=frame, expr=exprs[engine]: frame.select(expr)
                )
                assert_frame_equal(reference, output, check_exact=True)
                if iteration >= 0:
                    samples[engine].append(timing)
                del output
        medians = {
            engine: statistics.median(sample["wall_seconds"] for sample in runs)
            for engine, runs in samples.items()
        }
        report["cases"].append(
            {
                "name": case.name,
                "rows": frame.height,
                "output_rows": reference.height,
                "median_seconds": medians,
                "runs": samples,
            }
        )
        print(
            f"{case.name:28} {frame.height:>9,} rows {medians['baseline']/medians['polars']:.2f}x",
            flush=True,
        )
        args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
