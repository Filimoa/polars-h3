"""Matched DuckDB workloads, deterministic inputs and full-output validation."""

from __future__ import annotations

import struct
from collections.abc import Callable
from dataclasses import dataclass


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
        if left.height != right.height:
            raise AssertionError("different output heights")
        for offset in range(0, left.height, 8192):
            lhs = left.to_series().slice(offset, 8192).to_list()
            rhs = right.to_series().slice(offset, 8192).to_list()
            if [None if v is None else sorted(v) for v in lhs] != [
                None if v is None else sorted(v) for v in rhs
            ]:
                raise AssertionError(f"unordered results differ near row {offset}")
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


def _square_polygon_wkb(lat: float, lon: float, half_size: float = 0.015) -> bytes:
    """Build a little-endian WKB polygon centered on a latitude/longitude."""
    ring = [
        (lon - half_size, lat - half_size),
        (lon + half_size, lat - half_size),
        (lon + half_size, lat + half_size),
        (lon - half_size, lat + half_size),
        (lon - half_size, lat - half_size),
    ]
    value = bytearray(struct.pack("<BIII", 1, 3, 1, len(ring)))
    for lng, latitude in ring:
        value.extend(struct.pack("<dd", lng, latitude))
    return bytes(value)
