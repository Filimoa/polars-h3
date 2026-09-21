"""Compare equivalent H3 operations with materialized Polars output from both engines."""

import argparse
import hashlib
import json
import os
import platform
import statistics
import time
from pathlib import Path

import duckdb
import polars as pl
from polars.plugins import _resolve_plugin_path
from polars.testing import assert_frame_equal

import polars_h3.core.indexing as indexing
from benchmarks.kernel_profile import make_data, make_runner

SQL = {
    "get_resolution": "h3_get_resolution(cell)",
    "get_resolution_string": "h3_get_resolution(cell_string)",
    "is_valid_cell": "h3_is_valid_cell(cell)",
    "is_pentagon": "h3_is_pentagon(cell)",
    "is_res_class_III": "h3_is_res_class_iii(cell)",
    "cell_to_parent": "h3_cell_to_parent(cell, 8)",
    "cell_to_parent_string": "h3_cell_to_parent(cell_string, 8)",
    "cell_to_center_child": "h3_cell_to_center_child(cell, 10)",
    "cell_to_children_size": "h3_cell_to_children_size(cell, 10)",
    "cell_to_child_pos": "h3_cell_to_child_pos(cell, 8)",
    "latlng_to_cell": "h3_latlng_to_cell(lat, lng, 9)",
    "latlng_to_cell_string": "h3_latlng_to_cell_string(lat, lng, 9)",
    "cell_to_lat": "h3_cell_to_lat(cell)",
    "cell_to_lng": "h3_cell_to_lng(cell)",
    "cell_to_latlng": "h3_cell_to_latlng(cell)",
    "int_to_str": "h3_h3_to_string(cell)",
    "get_directed_edge_origin": "h3_get_directed_edge_origin(edge)",
    "get_directed_edge_destination": "h3_get_directed_edge_destination(edge)",
    "are_neighbor_cells": "h3_are_neighbor_cells(origin, destination)",
    "cells_to_directed_edge": "h3_cells_to_directed_edge(origin, destination)",
    "cell_to_vertex": "h3_cell_to_vertex(origin, 0)",
    "is_valid_vertex": "h3_is_valid_vertex(vertex)",
    "child_pos_to_cell": "h3_child_pos_to_cell(pos::BIGINT, cell, 10)",
    "grid_distance": "h3_grid_distance(origin, destination)",
}


def query(name, table):
    if name == "index_parent_resolution":
        return f"SELECT h3_cell_to_parent(cell, 8) AS parent, h3_get_resolution(cell) AS resolution FROM (SELECT h3_latlng_to_cell(lat, lng, 9) AS cell FROM {table})"
    return f"SELECT {SQL[name]} AS result FROM {table}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=25_000_000)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--threads", type=int, default=16)
    parser.add_argument("--arrow-batch-rows", type=int, default=None)
    parser.add_argument(
        "--functions", nargs="+", choices=[*SQL, "index_parent_resolution"]
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    con = duckdb.connect(config={"threads": args.threads})
    con.execute("LOAD h3")
    frame = make_data(args.rows, extended=True)
    arrow = frame.to_arrow()
    if args.arrow_batch_rows:
        arrow = type(arrow).from_batches(
            arrow.to_batches(max_chunksize=args.arrow_batch_rows)
        )
    con.register("arrow_input", arrow)
    con.execute("CREATE TABLE native_input AS SELECT * FROM arrow_input")
    plugin = _resolve_plugin_path(indexing.LIB)
    report = {
        "metadata": {
            "rows": args.rows,
            "iterations": args.iterations,
            "warmups": args.warmups,
            "polars_threads": pl.thread_pool_size(),
            "rayon_threads": os.environ.get("RAYON_NUM_THREADS", "default"),
            "duckdb_threads": con.execute(
                "SELECT current_setting('threads')"
            ).fetchone()[0],
            "platform": platform.platform(),
            "python": platform.python_version(),
            "polars": pl.__version__,
            "duckdb": duckdb.__version__,
            "duckdb_h3_extension": con.execute(
                "SELECT extension_version FROM duckdb_extensions() WHERE extension_name='h3'"
            ).fetchone()[0],
            "duckdb_h3": con.execute("SELECT h3_version()").fetchone()[0],
            "plugin": str(plugin),
            "sha256": hashlib.sha256(plugin.read_bytes()).hexdigest(),
            "input_chunks": frame.n_chunks(strategy="all"),
            "arrow_batch_rows": args.arrow_batch_rows,
            "arrow_chunks": [column.num_chunks for column in arrow.columns],
            "boundary": "Prepared queries; materialized Polars output; input preparation/registration/native table load, validation and output disposal excluded",
        },
        "results": [],
    }
    for name in args.functions or [*SQL, "index_parent_resolution"]:
        runners = {"polars_h3": make_runner(frame, name, "lazy")}
        for engine, table in [
            ("duckdb_arrow", "arrow_input"),
            ("duckdb_native", "native_input"),
        ]:
            relation = con.sql(query(name, table))
            runners[engine] = relation.pl
        expected = runners["polars_h3"]()
        validations = {}
        for engine, run in runners.items():
            out = run()
            schema = {k: str(v) for k, v in out.schema.items()}
            # Integer widths differ between APIs; normalize only after timing.
            normalized = out.cast(expected.schema)
            floating = name in {"cell_to_lat", "cell_to_lng", "cell_to_latlng"}
            assert_frame_equal(
                normalized,
                expected,
                check_exact=not floating,
                rel_tol=1e-12,
                abs_tol=1e-9,
            )
            validations[engine] = {
                "schema": schema,
                "normalized_fingerprint": normalized.hash_rows(seed=0).sum(),
                "floating_tolerance": floating,
            }
            del out, normalized
        del expected
        for run in runners.values():
            for _ in range(args.warmups):
                run()
        times = {k: [] for k in runners}
        cpu_times = {k: [] for k in runners}
        engines = list(runners)
        orders = []
        for iteration in range(args.iterations):
            order = engines[iteration % 3 :] + engines[: iteration % 3]
            if iteration % 2:
                order = order[::-1]
            orders.append(order)
            for engine in order:
                cpu_start = time.process_time()
                start = time.perf_counter()
                out = runners[engine]()
                times[engine].append((time.perf_counter() - start) * 1000)
                cpu_times[engine].append((time.process_time() - cpu_start) * 1000)
                del out
        result = {
            "name": name,
            "runs_ms": times,
            "cpu_runs_ms": cpu_times,
            "median_ms": {k: statistics.median(v) for k, v in times.items()},
            "validation": validations,
            "order": orders,
            "duckdb_sql": query(name, "arrow_input"),
        }
        report["results"].append(result)
        print(name, result["median_ms"], flush=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    con.close()


if __name__ == "__main__":
    main()
