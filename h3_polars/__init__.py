from __future__ import annotations
from typing import TYPE_CHECKING
from pathlib import Path
import polars as pl
from polars.plugins import register_plugin_function


if TYPE_CHECKING:
    from h3_polars.typing import IntoExprColumn

LIB = Path(__file__).parent


def latlng_to_cell(
    lat: IntoExprColumn, lng: IntoExprColumn, resolution: int
) -> pl.Expr:
    return register_plugin_function(
        args=[lat, lng],
        plugin_path=LIB,
        function_name="latlng_to_cell",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def latlng_to_cell_string(
    lat: IntoExprColumn, lng: IntoExprColumn, resolution: int
) -> pl.Expr:
    return register_plugin_function(
        args=[lat, lng],
        plugin_path=LIB,
        function_name="latlng_to_cell_string",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def cell_to_lat(cell: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_lat",
        is_elementwise=True,
    )


def cell_to_lng(cell: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_lng",
        is_elementwise=True,
    )


def cell_to_latlng(cell: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_latlng",
        is_elementwise=True,
    )


def get_resolution(expr: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="get_resolution",
        is_elementwise=True,
    )


def str_to_int(expr: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="str_to_int",
        is_elementwise=True,
    )


def int_to_str(expr: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="int_to_str",
        is_elementwise=True,
    )


def is_valid_cell(expr: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="is_valid_cell",
        is_elementwise=True,
    )


def is_pentagon(expr: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="is_pentagon",
        is_elementwise=True,
    )


def is_res_class_III(expr: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="is_res_class_III",
        is_elementwise=True,
    )


def get_icosahedron_faces(expr: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="get_icosahedron_faces",
        is_elementwise=True,
    )


def cell_to_parent(cell: IntoExprColumn, resolution: int | None = None) -> pl.Expr:
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_parent",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def cell_to_center_child(
    cell: IntoExprColumn, resolution: int | None = None
) -> pl.Expr:
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_center_child",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def cell_to_children_size(
    cell: IntoExprColumn, resolution: int | None = None
) -> pl.Expr:
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_children_size",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def cell_to_children(cell: IntoExprColumn, resolution: int) -> pl.Expr:
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_children",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def cell_to_child_pos(cell: IntoExprColumn, resolution: int = 0) -> pl.Expr:
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_child_pos",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def child_pos_to_cell(
    parent: IntoExprColumn, pos: IntoExprColumn, resolution: int = 0
) -> pl.Expr:
    return register_plugin_function(
        args=[parent, pos],
        plugin_path=LIB,
        function_name="child_pos_to_cell",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def compact_cells(cells: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[cells],
        plugin_path=LIB,
        function_name="compact_cells",
        is_elementwise=True,
    )


def uncompact_cells(cells: IntoExprColumn, resolution: int) -> pl.Expr:
    return register_plugin_function(
        args=[cells],
        plugin_path=LIB,
        function_name="uncompact_cells",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def grid_distance(origin: IntoExprColumn, destination: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[origin, destination],
        plugin_path=LIB,
        function_name="grid_distance",
    )


def grid_ring(cell: IntoExprColumn, k: int) -> pl.Expr:
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="grid_ring",
        kwargs={"k": k},
    )


def grid_disk(cell: IntoExprColumn, k: int) -> pl.Expr:
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="grid_disk",
        kwargs={"k": k},
    )


def grid_path_cells(origin: IntoExprColumn, destination: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[origin, destination],
        plugin_path=LIB,
        function_name="grid_path_cells",
    )


# ===== Vertexes ===== #


def cell_to_vertex(cell: IntoExprColumn, vertex_num: int) -> pl.Expr:
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_vertex",
        kwargs={"vertex_num": vertex_num},
    )


def cell_to_vertexes(cell: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_vertexes",
    )


def vertex_to_latlng(vertex: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[vertex],
        plugin_path=LIB,
        function_name="vertex_to_latlng",
    )


def is_valid_vertex(vertex: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[vertex],
        plugin_path=LIB,
        function_name="is_valid_vertex",
    )


# ===== Edge ===== #


def are_neighbor_cells(origin: IntoExprColumn, destination: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[origin, destination],
        plugin_path=LIB,
        function_name="are_neighbor_cells",
    )


def cells_to_directed_edge(
    origin: IntoExprColumn, destination: IntoExprColumn
) -> pl.Expr:
    return register_plugin_function(
        args=[origin, destination],
        plugin_path=LIB,
        function_name="cells_to_directed_edge",
    )


def is_valid_directed_edge(edge: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[edge],
        plugin_path=LIB,
        function_name="is_valid_directed_edge",
    )


def get_directed_edge_origin(edge: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[edge],
        plugin_path=LIB,
        function_name="get_directed_edge_origin",
    )


def get_directed_edge_destination(edge: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[edge],
        plugin_path=LIB,
        function_name="get_directed_edge_destination",
    )


def directed_edge_to_cells(edge: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[edge],
        plugin_path=LIB,
        function_name="directed_edge_to_cells",
    )


def origin_to_directed_edges(cell: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="origin_to_directed_edges",
    )


def directed_edge_to_boundary(edge: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[edge],
        plugin_path=LIB,
        function_name="directed_edge_to_boundary",
    )


# ===== Metrics ===== #

# get_hexagon_edge_length , get_hexagon_area, great_circle_distance are not implemented
