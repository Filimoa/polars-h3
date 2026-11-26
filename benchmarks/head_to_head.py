"""Matched large-data workloads; run --help for controls and timing contracts.

Heavy imports happen after thread settings are applied. No engine installation
or dataset creation is included in query timing. Correctness failures are fatal.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import importlib
import importlib.metadata
import json
import os
import platform
import random
import statistics
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Case:
    name: str
    columns: tuple[str, ...]
    expression: Callable
    sql: str
    category: str = "scalar"
    unordered: bool = False
    floating: bool = False


def cases(resolution: int, radius: int) -> dict[str, Case]:
    import polars as pl

    import polars_h3 as h

    r = resolution
    definitions = [
        Case("identity_u64", ("cell",), lambda: pl.col("cell"), "cell"),
        Case("identity_string", ("text",), lambda: pl.col("text"), "text"),
        Case(
            "latlng_to_cell",
            ("lat", "lng"),
            lambda: h.latlng_to_cell("lat", "lng", r),
            f"h3_latlng_to_cell(lat,lng,{r})",
        ),
        Case(
            "latlng_to_cell_string",
            ("lat", "lng"),
            lambda: h.latlng_to_cell("lat", "lng", r, return_dtype=pl.String),
            f"h3_latlng_to_cell_string(lat,lng,{r})",
        ),
        Case(
            "cell_to_lat",
            ("cell",),
            lambda: h.cell_to_lat("cell"),
            "h3_cell_to_lat(cell)",
            floating=True,
        ),
        Case(
            "cell_to_lng",
            ("cell",),
            lambda: h.cell_to_lng("cell"),
            "h3_cell_to_lng(cell)",
            floating=True,
        ),
        Case(
            "cell_to_latlng",
            ("cell",),
            lambda: h.cell_to_latlng("cell"),
            "h3_cell_to_latlng(cell)",
            floating=True,
        ),
        Case(
            "get_resolution",
            ("cell",),
            lambda: h.get_resolution("cell"),
            "h3_get_resolution(cell)",
        ),
        Case(
            "is_valid_cell",
            ("cell",),
            lambda: h.is_valid_cell("cell"),
            "h3_is_valid_cell(cell)",
        ),
        Case(
            "is_pentagon",
            ("cell",),
            lambda: h.is_pentagon("cell"),
            "h3_is_pentagon(cell)",
        ),
        Case(
            "is_res_class_III",
            ("cell",),
            lambda: h.is_res_class_III("cell"),
            "h3_is_res_class_iii(cell)",
        ),
        Case(
            "int_to_str",
            ("cell",),
            lambda: h.int_to_str("cell"),
            "h3_h3_to_string(cell)",
        ),
        Case(
            "str_to_int",
            ("text",),
            lambda: h.str_to_int("text"),
            "h3_string_to_h3(text)",
        ),
        Case(
            "cell_to_parent",
            ("cell",),
            lambda: h.cell_to_parent("cell", r - 1),
            f"h3_cell_to_parent(cell,{r-1})",
        ),
        Case(
            "string_cell_to_parent",
            ("text",),
            lambda: h.cell_to_parent("text", r - 1),
            f"h3_cell_to_parent(text,{r-1})",
        ),
        Case(
            "cell_to_center_child",
            ("cell",),
            lambda: h.cell_to_center_child("cell", r + 1),
            f"h3_cell_to_center_child(cell,{r+1})",
        ),
        Case(
            "cell_to_children_size",
            ("cell",),
            lambda: h.cell_to_children_size("cell", r + 1),
            f"h3_cell_to_children_size(cell,{r+1})",
        ),
        Case(
            "cell_to_children",
            ("cell",),
            lambda: h.cell_to_children("cell", r + 1),
            f"h3_cell_to_children(cell,{r+1})",
            "list",
            True,
        ),
        Case(
            "grid_disk",
            ("cell",),
            lambda: h.grid_disk("cell", radius),
            f"h3_grid_disk(cell,{radius})",
            "list",
            True,
        ),
        Case(
            "grid_ring",
            ("cell",),
            lambda: h.grid_ring("cell", radius),
            f"h3_grid_ring_unsafe(cell,{radius})",
            "list",
            True,
        ),
        Case(
            "grid_distance",
            ("cell", "neighbor"),
            lambda: h.grid_distance("cell", "neighbor"),
            "h3_grid_distance(cell,neighbor)",
        ),
        Case(
            "are_neighbor_cells",
            ("cell", "neighbor"),
            lambda: h.are_neighbor_cells("cell", "neighbor"),
            "h3_are_neighbor_cells(cell,neighbor)",
        ),
        Case(
            "cells_to_directed_edge",
            ("cell", "neighbor"),
            lambda: h.cells_to_directed_edge("cell", "neighbor"),
            "h3_cells_to_directed_edge(cell,neighbor)",
        ),
        Case(
            "origin_to_directed_edges",
            ("cell",),
            lambda: h.origin_to_directed_edges("cell"),
            "h3_origin_to_directed_edges(cell)",
            "list",
            True,
        ),
        Case(
            "get_directed_edge_origin",
            ("edge",),
            lambda: h.get_directed_edge_origin("edge"),
            "h3_get_directed_edge_origin(edge)",
        ),
        Case(
            "get_directed_edge_destination",
            ("edge",),
            lambda: h.get_directed_edge_destination("edge"),
            "h3_get_directed_edge_destination(edge)",
        ),
        Case(
            "directed_edge_to_cells",
            ("edge",),
            lambda: h.directed_edge_to_cells("edge"),
            "h3_directed_edge_to_cells(edge)",
            "list",
        ),
        Case(
            "cell_to_vertex",
            ("cell",),
            lambda: h.cell_to_vertex("cell", 0),
            "h3_cell_to_vertex(cell,0)",
        ),
        Case(
            "cell_to_vertexes",
            ("cell",),
            lambda: h.cell_to_vertexes("cell"),
            "h3_cell_to_vertexes(cell)",
            "list",
            True,
        ),
        Case(
            "cell_area",
            ("cell",),
            lambda: h.cell_area("cell"),
            "h3_cell_area(cell,'km^2')",
            floating=True,
        ),
        Case(
            "edge_length",
            ("edge",),
            lambda: h.edge_length("edge"),
            "h3_edge_length(edge,'km')",
            floating=True,
        ),
        Case(
            "index_parent",
            ("lat", "lng"),
            lambda: h.cell_to_parent(h.latlng_to_cell("lat", "lng", r), r - 2),
            f"h3_cell_to_parent(h3_latlng_to_cell(lat,lng,{r}),{r-2})",
        ),
        Case(
            "polygon_to_cells",
            ("polygon",),
            lambda: h.polygon_to_cells("polygon", r),
            f"h3_polygon_wkb_to_cells(polygon,{r})",
            "polygon",
            True,
        ),
    ]
    return {case.name: case for case in definitions}


def make_frame(case: Case, rows: int, resolution: int, layout: str, null_every: int):
    import polars as pl

    import polars_h3 as h

    # Relatively prime periods provide many distinct inputs, without Python
    # per-row objects or random-state dependence. Ordinary Ohio cells avoid
    # pentagon ring semantics; pathological inputs belong in correctness tests.
    frame = pl.DataFrame({"i": pl.int_range(0, rows, eager=True)}).select(
        lat=38.403 + (pl.col("i") * 8191 % 1_000_003) / 1_000_003 * 3.575,
        lng=-84.820 + (pl.col("i") * 131071 % 1_000_033) / 1_000_033 * 4.302,
    )
    columns = set(case.columns)
    if columns & {"cell", "text", "neighbor", "edge"}:
        frame = frame.with_columns(cell=h.latlng_to_cell("lat", "lng", resolution))
    if "text" in columns:
        frame = frame.with_columns(text=h.int_to_str("cell"))
    if columns & {"neighbor", "edge"}:
        frame = frame.with_columns(neighbor=h.grid_ring("cell", 1).list.get(0))
    if "edge" in columns:
        frame = frame.with_columns(edge=h.cells_to_directed_edge("cell", "neighbor"))
    if "polygon" in columns:
        from benchmarks.engine import _square_polygon_wkb

        frame = frame.with_columns(
            pl.Series(
                "polygon",
                [_square_polygon_wkb(lat, lng) for lat, lng in frame.iter_rows()],
                dtype=pl.Binary,
            )
        )
    # Input layout must not depend on the implementation being benchmarked:
    # setup expressions themselves can produce highly fragmented outputs.
    frame = frame.select(case.columns).rechunk()
    if null_every:
        frame = frame.select(
            pl.when(pl.int_range(pl.len()) % null_every == 0)
            .then(None)
            .otherwise(pl.all())
            .name.keep()
        )
    if layout == "chunked":
        frame = pl.concat(
            [frame.slice(i, 65536) for i in range(0, rows, 65536)], rechunk=False
        )
    elif layout == "sliced":
        # Nonzero array offset, including a non-byte-aligned validity offset.
        frame = pl.concat([frame.head(3), frame], rechunk=True).slice(3)
    return frame


def validate(case: Case, left, right) -> None:
    import polars as pl
    from polars.testing import assert_frame_equal

    if not isinstance(left, pl.DataFrame):
        left = pl.from_arrow(left)
    if not isinstance(right, pl.DataFrame):
        right = pl.from_arrow(right)
    # Width differences are API conventions, not different mathematical work.
    right = right.cast(left.schema)
    if case.unordered:
        # Polars list.sort dispatches a parallel sort for each tiny inner list
        # in some versions. A bounded Python comparison avoids that validation
        # bottleneck while still checking every cell, duplicate and null.
        assert left.height == right.height
        for offset in range(0, left.height, 8192):
            lhs = left.to_series().slice(offset, 8192).to_list()
            rhs = right.to_series().slice(offset, 8192).to_list()
            assert [None if v is None else sorted(v) for v in lhs] == [
                None if v is None else sorted(v) for v in rhs
            ], f"unordered results differ near row {offset}"
        return
    if case.floating and isinstance(left.to_series().dtype, pl.List):
        # Compare list structure, then all scalar values. Recursing through
        # millions of tiny coordinate lists is needlessly expensive.
        assert_frame_equal(
            left.select(pl.all().list.len()), right.select(pl.all().list.len())
        )
        left = left.select(pl.all().explode(empty_as_null=True))
        right = right.select(pl.all().explode(empty_as_null=True))
    assert_frame_equal(
        left, right, check_exact=not case.floating, rel_tol=1e-7, abs_tol=1e-9
    )


def measure(call: Callable) -> tuple[Any, dict]:
    start_cpu = time.process_time()
    start = time.perf_counter()
    output = call()
    wall = time.perf_counter() - start
    cpu = time.process_time() - start_cpu
    return output, {"wall_seconds": wall, "cpu_seconds": cpu}


def use_plugin(path: Path | None) -> None:
    import polars_h3

    selected = path or Path(polars_h3.__file__).parent
    for module in (
        "indexing",
        "inspection",
        "traversal",
        "edge",
        "vertexes",
        "metrics",
        "geometry",
    ):
        importlib.import_module(f"polars_h3.core.{module}").LIB = selected


def run_case(case: Case, args, con) -> dict:
    import pyarrow as pa

    rows = {"scalar": args.rows, "list": args.list_rows, "polygon": args.polygon_rows}[
        case.category
    ]
    frame, generation = measure(
        lambda: make_frame(case, rows, args.resolution, args.layout, args.null_every)
    )
    arrow, conversion = measure(frame.to_arrow)
    # Chunked Arrow lets DuckDB distribute batches rather than bottleneck on a
    # single Arrow chunk. Construct the table once; readers are one-shot objects.
    arrow = pa.Table.from_batches(arrow.to_batches(max_chunksize=args.arrow_batch_rows))
    con.register("arrow_input", arrow)
    _, loading = measure(
        lambda: con.execute(
            "CREATE OR REPLACE TEMP TABLE input AS SELECT * FROM arrow_input"
        )
    )
    expr = case.expression().alias("result")
    expressions = {"polars": expr}
    if args.baseline_plugin:
        use_plugin(args.baseline_plugin)
        expressions["baseline"] = case.expression().alias("result")
        use_plugin(args.plugin_path)
    reference = frame.select(expr)
    sql = f"SELECT {case.sql} AS result FROM input"
    validate(case, reference, con.execute(sql).fetch_arrow_table())
    records = []
    for mode in args.modes:
        source = "arrow_input" if mode == "arrow-scan" else "input"
        query = f"SELECT {case.sql} AS result FROM {source}"

        def polars_run(engine, mode=mode):
            result = frame.select(expressions[engine])
            return result if mode == "resident" else result.to_arrow()

        def duckdb_run(mode=mode, query=query):
            if mode in ("resident", "arrow-materialized"):
                con.execute(f"CREATE TEMP TABLE output AS {query}")
                return (
                    None
                    if mode == "resident"
                    else con.execute("SELECT * FROM output").fetch_arrow_table()
                )
            return con.execute(query).fetch_arrow_table()

        samples = {engine: [] for engine in [*expressions, "duckdb"]}
        for iteration in range(-args.warmups, args.iterations):
            order = list(samples)
            # Rotate and reverse to balance first/last engine position.
            shift = iteration % len(order)
            order = order[shift:] + order[:shift]
            if iteration % 2:
                order.reverse()
            for engine in order:
                if engine == "duckdb" and mode in ("resident", "arrow-materialized"):
                    con.execute("DROP TABLE IF EXISTS output")
                gc.collect()
                output, timing = measure(
                    duckdb_run
                    if engine == "duckdb"
                    else lambda engine=engine: polars_run(engine)
                )
                if iteration >= 0:
                    samples[engine].append(timing)
                # Validate every timed output outside the measured interval.
                if output is None:
                    output = con.execute("SELECT * FROM output").fetch_arrow_table()
                timing["output_chunks"] = (
                    output.n_chunks()
                    if hasattr(output, "n_chunks")
                    else output.column(0).num_chunks
                )
                validate(case, reference, output)
                del output
        for engine, runs in samples.items():
            walls = [run["wall_seconds"] for run in runs]
            records.append(
                {
                    "mode": mode,
                    "engine": engine,
                    "median_seconds": statistics.median(walls),
                    "min_seconds": min(walls),
                    "max_seconds": max(walls),
                    "runs": runs,
                }
            )
        current = {
            result["engine"]: result for result in records if result["mode"] == mode
        }
        a, b = current["polars"], current["duckdb"]
        gain = (
            f" before/after={current['baseline']['median_seconds']/a['median_seconds']:.2f}x"
            if "baseline" in current
            else ""
        )
        print(
            f"{case.name:28} {rows:>10,} {mode:12} polars={a['median_seconds']:.5f}s duckdb={b['median_seconds']:.5f}s ratio={b['median_seconds']/a['median_seconds']:.2f}x{gain}",
            flush=True,
        )
    result = {
        "name": case.name,
        "rows": rows,
        "sql": sql,
        "polars_expression": str(expr),
        "input_schema": {name: str(dtype) for name, dtype in frame.schema.items()},
        "input_chunks": frame.n_chunks(),
        "input_bytes": frame.estimated_size(),
        "output_bytes": reference.estimated_size(),
        "output_chunks": reference.n_chunks(),
        "setup": {
            "generation": generation,
            "to_arrow": conversion,
            "duckdb_native_load": loading,
        },
        "validation": "all rows, every output",
        "results": records,
    }
    con.unregister("arrow_input")
    con.execute("DROP TABLE IF EXISTS output")
    con.execute("DROP TABLE input")
    return result


def metadata(args, con) -> dict:
    import polars as pl
    from polars.plugins import _resolve_plugin_path

    import polars_h3

    # Use the same resolver as register_plugin_function, including Windows.
    # A development checkout can contain stale extension binaries as well.
    binary = _resolve_plugin_path(
        args.plugin_path or Path(polars_h3.__file__).parent, use_abs_path=True
    )
    return {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpus": os.cpu_count(),
        "versions": {
            name: importlib.metadata.version(name)
            for name in ("polars", "polars-h3", "duckdb", "pyarrow", "h3")
        },
        "duckdb_h3": con.execute(
            "SELECT extension_version FROM duckdb_extensions() WHERE extension_name='h3'"
        ).fetchone()[0],
        "h3_core": con.execute("SELECT h3_version()").fetchone()[0],
        "polars_threads": pl.thread_pool_size(),
        "rayon_threads": os.environ["RAYON_NUM_THREADS"],
        "duckdb_threads": con.execute("SELECT current_setting('threads')").fetchone()[
            0
        ],
        "rustc": subprocess.check_output(["rustc", "--version"], text=True).strip(),
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "git_status": subprocess.check_output(["git", "status", "--short"], text=True),
        "binary": str(binary),
        "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
        "baseline_binary_sha256": hashlib.sha256(
            args.baseline_plugin.read_bytes()
        ).hexdigest()
        if args.baseline_plugin
        else None,
        "settings": {
            key: str(value) if isinstance(value, Path) else value
            for key, value in vars(args).items()
        },
        "timing_contracts": {
            "resident": "Preloaded inputs; Polars select materializes a DataFrame, DuckDB CTAS materializes a temporary native table. No output export. Not pure kernel time: allocators and storage differ.",
            "arrow-materialized": "Preloaded native inputs; Polars select then Arrow export; DuckDB CTAS then SELECT/export of that result, all timed. Materializing before export allows parallel H3 computation in DuckDB.",
            "arrow-output": "Preloaded native inputs, full query execution and Arrow result materialization for both engines.",
            "arrow-scan": "Polars native frame versus DuckDB registered batched Arrow input; both fully materialize Arrow output. Interoperability scenario, not native DuckDB throughput.",
            "setup": "Input generation, Polars-to-Arrow, native DuckDB ingestion timed separately and excluded from query samples.",
        },
    }


def positive(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=positive, default=5_000_000)
    parser.add_argument("--list-rows", type=positive, default=250_000)
    parser.add_argument("--polygon-rows", type=positive, default=2_000)
    parser.add_argument("--threads", type=positive, default=8)
    parser.add_argument("--iterations", type=positive, default=5)
    parser.add_argument("--warmups", type=positive, default=2)
    parser.add_argument("--resolution", type=int, choices=range(2, 15), default=9)
    parser.add_argument("--radius", type=positive, default=3)
    parser.add_argument("--arrow-batch-rows", type=positive, default=65536)
    parser.add_argument("--functions", nargs="+", default=["all"])
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=["resident", "arrow-materialized", "arrow-output", "arrow-scan"],
        default=["resident", "arrow-materialized"],
    )
    parser.add_argument(
        "--layout", choices=["contiguous", "chunked", "sliced"], default="contiguous"
    )
    parser.add_argument("--null-every", type=int, default=0)
    parser.add_argument("--install-extension", action="store_true")
    parser.add_argument(
        "--plugin-path",
        type=Path,
        help="Explicit saved plugin binary for reproducible before/after runs",
    )
    parser.add_argument(
        "--baseline-plugin",
        type=Path,
        help="Saved original binary to interleave with the current plugin and DuckDB",
    )
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.null_every < 0:
        parser.error("--null-every cannot be negative")
    os.environ["POLARS_MAX_THREADS"] = str(args.threads)
    os.environ["RAYON_NUM_THREADS"] = str(args.threads)
    import duckdb

    for name in ("plugin_path", "baseline_plugin"):
        path = getattr(args, name)
        if path:
            if not path.is_file():
                parser.error(
                    f"--{name.replace('_', '-')} must be an existing plugin binary"
                )
            setattr(args, name, path.resolve())
    use_plugin(args.plugin_path)

    suite = cases(args.resolution, args.radius)
    names = list(suite) if args.functions == ["all"] else args.functions
    if unknown := set(names) - suite.keys():
        parser.error(f"unknown functions: {sorted(unknown)}")
    if args.output.exists():
        parser.error(
            "output already exists; choose a new path to preserve previous evidence"
        )
    con = duckdb.connect(config={"threads": args.threads})
    if args.install_extension:
        con.execute("INSTALL h3 FROM community")
    con.execute("LOAD h3")
    report = {"metadata": metadata(args, con), "cases": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Fixed shuffle avoids a permanent easy-to-hard order without losing reproducibility.
    random.Random(42).shuffle(names)
    for name in names:
        report["cases"].append(run_case(suite[name], args, con))
        args.output.write_text(json.dumps(report, indent=2) + "\n")
    con.close()


if __name__ == "__main__":
    main()
