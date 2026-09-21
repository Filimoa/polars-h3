"""Reproducible kernel/pipeline timings; optionally repeat a case for CPU sampling.

Run each library in a fresh process, with POLARS_MAX_THREADS and
RAYON_NUM_THREADS fixed. Example:
    uv run --no-sync -m benchmarks.kernel_profile --output /tmp/before.json
    uv run --no-sync -m benchmarks.kernel_profile --repeat get_resolution \
        --rows 1000000 --layouts fragmented --modes lazy --duration 10
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import platform
import resource
import statistics
import time
from pathlib import Path

import polars as pl
from polars.plugins import _resolve_plugin_path

import polars_h3 as h3


def use_plugin(path: Path) -> None:
    """Select an explicitly preserved shared library without reinstalling it."""
    for name in ["indexing", "inspection", "traversal", "metrics", "edge", "vertexes"]:
        module = importlib.import_module(f"polars_h3.core.{name}")
        module.LIB = path.resolve()


def make_data(rows: int, extended: bool = False) -> pl.DataFrame:
    frame = pl.DataFrame({"i": pl.int_range(0, rows, eager=True)})
    frame = frame.with_columns(
        lat=38.403 + (pl.col("i") % 3575) / 3575 * 3.575,
        lng=-84.820 + (pl.col("i") % 4302) / 4302 * 4.302,
    ).drop("i")
    frame = (
        frame.with_columns(cell=h3.latlng_to_cell("lat", "lng", 9))
        .with_columns(cell_string=h3.int_to_str("cell"))
        .rechunk()
    )
    if extended:
        frame = (
            frame.with_columns(
                origin=h3.cell_to_center_child("cell", 10),
                destination=h3.child_pos_to_cell(
                    "cell", pl.repeat(1, pl.len(), dtype=pl.UInt64), 10
                ),
                pos=(pl.int_range(pl.len(), dtype=pl.UInt64) % 7),
            )
            .with_columns(
                edge=h3.cells_to_directed_edge("origin", "destination"),
                vertex=h3.cell_to_vertex("origin", 0),
            )
            .rechunk()
        )
    return frame


def prepare(frame: pl.DataFrame, layout: str) -> pl.DataFrame:
    if layout == "nullable":
        index = pl.int_range(pl.len())
        frame = frame.with_columns(
            cell=pl.when(index % 11 == 0)
            .then(None)
            .when(index % 17 == 0)
            .then(pl.lit(0, dtype=pl.UInt64))
            .otherwise("cell"),
            cell_string=pl.when(index % 11 == 0)
            .then(None)
            .when(index % 17 == 0)
            .then(pl.lit("invalid"))
            .otherwise("cell_string"),
            lat=pl.when(index % 11 == 0).then(None).otherwise("lat"),
            lng=pl.when(index % 17 == 0).then(float("nan")).otherwise("lng"),
        )
        if "edge" in frame.columns:
            frame = frame.with_columns(
                pl.when(index % 11 == 0)
                .then(None)
                .when(index % 17 == 0)
                .then(pl.lit(0, pl.UInt64))
                .otherwise(pl.col(name))
                .alias(name)
                for name in ["origin", "destination", "edge", "vertex", "pos"]
            )
    if layout == "fragmented":
        size = max(1, (frame.height + 255) // 256)
        frame = pl.concat(
            [frame.slice(offset, size) for offset in range(0, frame.height, size)],
            rechunk=False,
        )
    return frame


def expressions() -> dict[str, pl.Expr]:
    return {
        "get_resolution": h3.get_resolution("cell"),
        "get_resolution_string": h3.get_resolution("cell_string"),
        "is_valid_cell": h3.is_valid_cell("cell"),
        "is_pentagon": h3.is_pentagon("cell"),
        "is_res_class_III": h3.is_res_class_III("cell"),
        "cell_to_parent": h3.cell_to_parent("cell", 8),
        "cell_to_parent_string": h3.cell_to_parent("cell_string", 8),
        "cell_to_center_child": h3.cell_to_center_child("cell", 10),
        "cell_to_children_size": h3.cell_to_children_size("cell", 10),
        "cell_to_child_pos": h3.cell_to_child_pos("cell", 8),
        "latlng_to_cell": h3.latlng_to_cell("lat", "lng", 9),
        "latlng_to_cell_string": h3.latlng_to_cell(
            "lat", "lng", 9, return_dtype=pl.String
        ),
        "cell_to_lat": h3.cell_to_lat("cell"),
        "cell_to_lng": h3.cell_to_lng("cell"),
        "cell_to_latlng": h3.cell_to_latlng("cell"),
        "int_to_str": h3.int_to_str("cell"),
    }


def extended_expressions() -> dict[str, pl.Expr]:
    return {
        "get_directed_edge_origin": h3.get_directed_edge_origin("edge"),
        "get_directed_edge_destination": h3.get_directed_edge_destination("edge"),
        "are_neighbor_cells": h3.are_neighbor_cells("origin", "destination"),
        "cells_to_directed_edge": h3.cells_to_directed_edge("origin", "destination"),
        "cell_to_vertex": h3.cell_to_vertex("origin", 0),
        "is_valid_vertex": h3.is_valid_vertex("vertex"),
        "child_pos_to_cell": h3.child_pos_to_cell("cell", "pos", 10),
        "grid_distance": h3.grid_distance("origin", "destination"),
    }


def make_runner(frame: pl.DataFrame, name: str, mode: str):
    if name == "index_parent_resolution":
        if mode == "eager":
            return lambda: frame.select(cell=h3.latlng_to_cell("lat", "lng", 9)).select(
                parent=h3.cell_to_parent("cell", 8),
                resolution=h3.get_resolution("cell"),
            )
        query = (
            frame.lazy()
            .select(cell=h3.latlng_to_cell("lat", "lng", 9))
            .select(
                parent=h3.cell_to_parent("cell", 8),
                resolution=h3.get_resolution("cell"),
            )
        )
    else:
        expr = {**expressions(), **extended_expressions()}[name].alias("result")
        if mode == "eager":
            return lambda: frame.select(expr)
        query = frame.lazy().select(expr)
    return lambda: query.collect(engine="streaming" if mode == "streaming" else "auto")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--rows", nargs="+", type=int, default=[1_000, 1_000_000])
    parser.add_argument(
        "--layouts",
        nargs="+",
        choices=["contiguous", "fragmented", "nullable"],
        default=["contiguous", "fragmented", "nullable"],
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=["eager", "lazy", "streaming"],
        default=["eager", "lazy"],
    )
    parser.add_argument("--functions", nargs="+")
    parser.add_argument(
        "--extended",
        action="store_true",
        help="Include edge, vertex, and paired-cell kernels",
    )
    parser.add_argument("--iterations", type=int, default=7)
    parser.add_argument("--warmups", type=int, default=3)
    parser.add_argument(
        "--repeat",
        choices=[*expressions(), *extended_expressions(), "index_parent_resolution"],
    )
    parser.add_argument("--duration", type=float, default=10)
    parser.add_argument("--ready-file", type=Path)
    args = parser.parse_args()
    if args.plugin:
        use_plugin(args.plugin)

    plugin = _resolve_plugin_path(
        importlib.import_module("polars_h3.core.indexing").LIB
    )
    functions = (
        [args.repeat]
        if args.repeat
        else args.functions or [*expressions(), "index_parent_resolution"]
    )
    if args.extended and not args.functions and not args.repeat:
        functions.extend(extended_expressions())
    data = make_data(
        max(args.rows), bool(set(functions) & extended_expressions().keys())
    )
    metadata = {
        "polars": pl.__version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "polars_threads": pl.thread_pool_size(),
        "rayon_threads": os.environ.get("RAYON_NUM_THREADS", "default"),
        "plugin": str(plugin),
        "sha256": hashlib.sha256(plugin.read_bytes()).hexdigest(),
        "warmups": args.warmups,
        "iterations": args.iterations,
    }
    if args.repeat:
        frame = prepare(data.head(args.rows[0]), args.layouts[0])
        run = make_runner(frame, args.repeat, args.modes[0])
        run()
        if args.ready_file:
            args.ready_file.write_text(str(os.getpid()))
        deadline = time.perf_counter() + args.duration
        count = 0
        while time.perf_counter() < deadline:
            run()
            count += 1
        print(json.dumps({**metadata, "calls": count, "duration": args.duration}))
        return

    results = []
    for rows in args.rows:
        for layout in args.layouts:
            # Small fragmented/null batches are covered by regression tests.
            if rows < 10_000 and layout != "contiguous":
                continue
            frame = prepare(data.head(rows), layout)
            for mode in args.modes:
                for name in functions:
                    run = make_runner(frame, name, mode)
                    for _ in range(args.warmups):
                        run()
                    times = []
                    cpu_times = []
                    for _ in range(args.iterations):
                        cpu_start = time.process_time()
                        start = time.perf_counter()
                        out = run()
                        times.append((time.perf_counter() - start) * 1_000)
                        cpu_times.append((time.process_time() - cpu_start) * 1_000)
                        del out
                    out = run()
                    assert out.height == rows
                    result = {
                        "name": name,
                        "rows": rows,
                        "layout": layout,
                        "mode": mode,
                        "median_ms": statistics.median(times),
                        "runs_ms": times,
                        "median_cpu_ms": statistics.median(cpu_times),
                        "input_chunks": frame.n_chunks(strategy="all"),
                        "output_chunks": out.n_chunks(strategy="all"),
                        "schema": {k: str(v) for k, v in out.schema.items()},
                        "fingerprint": out.hash_rows(seed=0).sum(),
                    }
                    results.append(result)
                    print(
                        f"{name:26} {rows:9,} {layout:10} {mode:9} {result['median_ms']:9.3f} ms",
                        flush=True,
                    )
    report = {
        "metadata": metadata,
        "results": results,
        "process_max_rss": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
