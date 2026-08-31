from __future__ import annotations

import argparse
import gc
import json
import statistics
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

import polars as pl

import polars_h3 as plh3

RESOLUTION = 9


@dataclass(frozen=True)
class Case:
    name: str
    rows: int
    expr: Callable[[], pl.Expr]


@dataclass
class Result:
    name: str
    rows: int
    avg_seconds: float
    std_seconds: float
    runs: list[float]


def make_data(max_rows: int) -> pl.DataFrame:
    idx = pl.int_range(0, max_rows, eager=True).cast(pl.Float64)
    df = (
        pl.DataFrame({"i": idx})
        .with_columns(
            lat=38.403 + (pl.col("i") % 3575) / 3575 * (41.978 - 38.403),
            lon=-84.820 + (pl.col("i") % 4302) / 4302 * (-80.518 + 84.820),
            lat2=38.403 + ((pl.col("i") + 17) % 3575) / 3575 * (41.978 - 38.403),
            lon2=-84.820 + ((pl.col("i") + 17) % 4302) / 4302 * (-80.518 + 84.820),
            resolution=(pl.col("i") % 16).cast(pl.UInt64),
            resolution_i64=(pl.col("i") % 16).cast(pl.Int64),
            local_i=(pl.col("i") % 3).cast(pl.Int32),
            local_j=((pl.col("i") + 1) % 3).cast(pl.Int32),
            child_pos=pl.lit(0, dtype=pl.UInt64),
        )
        .drop("i")
    )

    return df.with_columns(
        int_h3_cell=plh3.latlng_to_cell("lat", "lon", RESOLUTION),
        int_h3_cell_end=plh3.latlng_to_cell("lat2", "lon2", RESOLUTION),
        str_h3_cell=plh3.latlng_to_cell(
            "lat", "lon", RESOLUTION, return_dtype=pl.String
        ),
    )


def cases() -> dict[str, Case]:
    return {
        "latlng_to_cell": Case(
            "latlng_to_cell",
            8_000_000,
            lambda: plh3.latlng_to_cell("lat", "lon", RESOLUTION),
        ),
        "latlng_to_cell_string": Case(
            "latlng_to_cell_string",
            8_000_000,
            lambda: plh3.latlng_to_cell(
                "lat", "lon", RESOLUTION, return_dtype=pl.String
            ),
        ),
        "cell_to_lat": Case(
            "cell_to_lat", 8_000_000, lambda: plh3.cell_to_lat("int_h3_cell")
        ),
        "cell_to_lng": Case(
            "cell_to_lng", 8_000_000, lambda: plh3.cell_to_lng("int_h3_cell")
        ),
        "cell_to_latlng": Case(
            "cell_to_latlng", 8_000_000, lambda: plh3.cell_to_latlng("int_h3_cell")
        ),
        "cell_to_boundary": Case(
            "cell_to_boundary",
            2_000_000,
            lambda: plh3.cell_to_boundary("int_h3_cell"),
        ),
        "get_resolution": Case(
            "get_resolution", 8_000_000, lambda: plh3.get_resolution("int_h3_cell")
        ),
        "str_to_int": Case(
            "str_to_int", 8_000_000, lambda: plh3.str_to_int("str_h3_cell")
        ),
        "int_to_str": Case(
            "int_to_str", 8_000_000, lambda: plh3.int_to_str("int_h3_cell")
        ),
        "is_valid_cell": Case(
            "is_valid_cell", 8_000_000, lambda: plh3.is_valid_cell("int_h3_cell")
        ),
        "is_pentagon": Case(
            "is_pentagon", 8_000_000, lambda: plh3.is_pentagon("int_h3_cell")
        ),
        "is_res_class_III": Case(
            "is_res_class_III", 8_000_000, lambda: plh3.is_res_class_III("int_h3_cell")
        ),
        "get_icosahedron_faces": Case(
            "get_icosahedron_faces",
            4_000_000,
            lambda: plh3.get_icosahedron_faces("int_h3_cell"),
        ),
        "cell_to_parent": Case(
            "cell_to_parent",
            8_000_000,
            lambda: plh3.cell_to_parent("int_h3_cell", RESOLUTION - 1),
        ),
        "cell_to_center_child": Case(
            "cell_to_center_child",
            8_000_000,
            lambda: plh3.cell_to_center_child("int_h3_cell", RESOLUTION + 1),
        ),
        "cell_to_children_size": Case(
            "cell_to_children_size",
            8_000_000,
            lambda: plh3.cell_to_children_size("int_h3_cell", RESOLUTION + 1),
        ),
        "cell_to_children": Case(
            "cell_to_children",
            4_000_000,
            lambda: plh3.cell_to_children("int_h3_cell", RESOLUTION + 1),
        ),
        "cell_to_child_pos": Case(
            "cell_to_child_pos",
            8_000_000,
            lambda: plh3.cell_to_child_pos("child", RESOLUTION),
        ),
        "child_pos_to_cell": Case(
            "child_pos_to_cell",
            8_000_000,
            lambda: plh3.child_pos_to_cell("int_h3_cell", "child_pos", RESOLUTION + 1),
        ),
        "compact_cells": Case(
            "compact_cells", 500_000, lambda: plh3.compact_cells("cell_list")
        ),
        "uncompact_cells": Case(
            "uncompact_cells",
            500_000,
            lambda: plh3.uncompact_cells("cell_list", RESOLUTION + 1),
        ),
        "grid_distance": Case(
            "grid_distance",
            8_000_000,
            lambda: plh3.grid_distance("int_h3_cell", "int_h3_cell_end"),
        ),
        "grid_ring": Case(
            "grid_ring", 2_500_000, lambda: plh3.grid_ring("int_h3_cell", 3)
        ),
        "grid_disk": Case(
            "grid_disk", 1_500_000, lambda: plh3.grid_disk("int_h3_cell", 3)
        ),
        "grid_path_cells": Case(
            "grid_path_cells",
            100_000,
            lambda: plh3.grid_path_cells("int_h3_cell", "int_h3_cell_end"),
        ),
        "cell_to_local_ij": Case(
            "cell_to_local_ij",
            8_000_000,
            lambda: plh3.cell_to_local_ij("int_h3_cell", "int_h3_cell"),
        ),
        "local_ij_to_cell": Case(
            "local_ij_to_cell",
            8_000_000,
            lambda: plh3.local_ij_to_cell("int_h3_cell", "local_i", "local_j"),
        ),
        "cell_area": Case(
            "cell_area", 8_000_000, lambda: plh3.cell_area("int_h3_cell")
        ),
        "great_circle_distance": Case(
            "great_circle_distance",
            8_000_000,
            lambda: plh3.great_circle_distance("lat", "lon", "lat2", "lon2"),
        ),
        "average_hexagon_area": Case(
            "average_hexagon_area",
            8_000_000,
            lambda: plh3.average_hexagon_area("resolution"),
        ),
        "average_hexagon_edge_length": Case(
            "average_hexagon_edge_length",
            8_000_000,
            lambda: plh3.average_hexagon_edge_length("resolution"),
        ),
        "get_num_cells": Case(
            "get_num_cells", 8_000_000, lambda: plh3.get_num_cells("resolution")
        ),
        "get_pentagons": Case(
            "get_pentagons", 4_000_000, lambda: plh3.get_pentagons("resolution_i64")
        ),
        "are_neighbor_cells": Case(
            "are_neighbor_cells",
            8_000_000,
            lambda: plh3.are_neighbor_cells("int_h3_cell", "neighbor"),
        ),
        "cells_to_directed_edge": Case(
            "cells_to_directed_edge",
            8_000_000,
            lambda: plh3.cells_to_directed_edge("int_h3_cell", "neighbor"),
        ),
        "is_valid_directed_edge": Case(
            "is_valid_directed_edge",
            8_000_000,
            lambda: plh3.is_valid_directed_edge("edge"),
        ),
        "get_directed_edge_origin": Case(
            "get_directed_edge_origin",
            8_000_000,
            lambda: plh3.get_directed_edge_origin("edge"),
        ),
        "get_directed_edge_destination": Case(
            "get_directed_edge_destination",
            8_000_000,
            lambda: plh3.get_directed_edge_destination("edge"),
        ),
        "directed_edge_to_cells": Case(
            "directed_edge_to_cells",
            4_000_000,
            lambda: plh3.directed_edge_to_cells("edge"),
        ),
        "origin_to_directed_edges": Case(
            "origin_to_directed_edges",
            4_000_000,
            lambda: plh3.origin_to_directed_edges("int_h3_cell"),
        ),
        "directed_edge_to_boundary": Case(
            "directed_edge_to_boundary",
            2_000_000,
            lambda: plh3.directed_edge_to_boundary("edge"),
        ),
        "edge_length": Case("edge_length", 8_000_000, lambda: plh3.edge_length("edge")),
        "cell_to_vertex": Case(
            "cell_to_vertex", 8_000_000, lambda: plh3.cell_to_vertex("int_h3_cell", 0)
        ),
        "cell_to_vertexes": Case(
            "cell_to_vertexes", 4_000_000, lambda: plh3.cell_to_vertexes("int_h3_cell")
        ),
        "vertex_to_latlng": Case(
            "vertex_to_latlng", 8_000_000, lambda: plh3.vertex_to_latlng("vertex")
        ),
        "is_valid_vertex": Case(
            "is_valid_vertex", 8_000_000, lambda: plh3.is_valid_vertex("vertex")
        ),
    }


def run_case(df: pl.DataFrame, case: Case, iterations: int) -> Result:
    frame = prepare_frame(df.head(case.rows), case.name)
    rows = frame.height
    times: list[float] = []

    for _ in range(iterations):
        gc.collect()
        start = time.perf_counter()
        out = frame.with_columns(result=case.expr())
        out.select("result").head(1)
        times.append(time.perf_counter() - start)
        del out

    return Result(
        name=case.name,
        rows=rows,
        avg_seconds=statistics.mean(times),
        std_seconds=statistics.stdev(times) if len(times) > 1 else 0.0,
        runs=times,
    )


def prepare_frame(frame: pl.DataFrame, name: str) -> pl.DataFrame:
    needs_neighbor = {
        "are_neighbor_cells",
        "cells_to_directed_edge",
    }
    needs_edge = {
        "is_valid_directed_edge",
        "get_directed_edge_origin",
        "get_directed_edge_destination",
        "directed_edge_to_cells",
        "directed_edge_to_boundary",
        "edge_length",
    }
    needs_vertex = {
        "vertex_to_latlng",
        "is_valid_vertex",
    }
    needs_child = {"cell_to_child_pos"}
    needs_cell_list = {"compact_cells", "uncompact_cells"}

    if name in needs_neighbor or name in needs_edge:
        frame = frame.with_columns(
            neighbor=plh3.grid_ring("int_h3_cell", 1).list.get(1)
        )
    if name in needs_edge:
        frame = frame.with_columns(
            edge=plh3.cells_to_directed_edge("int_h3_cell", "neighbor")
        )
    if name in needs_vertex:
        frame = frame.with_columns(vertex=plh3.cell_to_vertex("int_h3_cell", 0))
    if name in needs_child:
        frame = frame.with_columns(
            child=plh3.cell_to_center_child("int_h3_cell", RESOLUTION + 1)
        )
    if name in needs_cell_list:
        frame = frame.with_columns(cell_list=plh3.grid_disk("int_h3_cell", 1))

    return frame


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Large plh3-only benchmarks")
    parser.add_argument("--functions", "-f", nargs="+", default=["all"])
    parser.add_argument("--iterations", "-n", type=int, default=3)
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--output", "-o", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    all_cases = cases()
    selected = (
        list(all_cases.values())
        if "all" in args.functions
        else [all_cases[name] for name in args.functions]
    )
    max_rows = args.max_rows or max(case.rows for case in selected)

    print(f"Generating {max_rows:,} rows")
    df = make_data(max_rows)

    results = [run_case(df, case, args.iterations) for case in selected]

    print(f"{'function':<28} {'rows':>10} {'avg':>10} {'std':>10}")
    for result in results:
        print(
            f"{result.name:<28} {result.rows:>10,} "
            f"{result.avg_seconds:>9.3f}s {result.std_seconds:>9.3f}s"
        )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps([asdict(result) for result in results], indent=2)
        )


if __name__ == "__main__":
    main()
