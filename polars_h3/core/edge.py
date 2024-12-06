from __future__ import annotations

from typing import TYPE_CHECKING
from pathlib import Path

import polars as pl
from polars.plugins import register_plugin_function


if TYPE_CHECKING:
    from polars_h3.typing import IntoExprColumn


LIB = Path(__file__).parent.parent


def are_neighbor_cells(origin: IntoExprColumn, destination: IntoExprColumn) -> pl.Expr:
    """
    Determines whether or not the provided H3 cells are neighbors.
    """
    return register_plugin_function(
        args=[origin, destination],
        plugin_path=LIB,
        function_name="are_neighbor_cells",
    )


def cells_to_directed_edge(
    origin: IntoExprColumn, destination: IntoExprColumn
) -> pl.Expr:
    """
    Provides a directed edge H3 index based on the provided origin and destination.
    """
    return register_plugin_function(
        args=[origin, destination],
        plugin_path=LIB,
        function_name="cells_to_directed_edge",
    )


def is_valid_directed_edge(edge: IntoExprColumn) -> pl.Expr:
    """
    Determines if the provided H3Index is a valid unidirectional edge index.
    """
    return register_plugin_function(
        args=[edge],
        plugin_path=LIB,
        function_name="is_valid_directed_edge",
    )


def get_directed_edge_origin(edge: IntoExprColumn) -> pl.Expr:
    """
    Provides the origin hexagon from the directed edge H3Index.
    """
    return register_plugin_function(
        args=[edge],
        plugin_path=LIB,
        function_name="get_directed_edge_origin",
    )


def get_directed_edge_destination(edge: IntoExprColumn) -> pl.Expr:
    """
    Provides the destination hexagon from the directed edge H3Index.
    """
    return register_plugin_function(
        args=[edge],
        plugin_path=LIB,
        function_name="get_directed_edge_destination",
    )


def directed_edge_to_cells(edge: IntoExprColumn) -> pl.Expr:
    """
    Provides the origin-destination pair of cells for the given directed edge.
    """
    return register_plugin_function(
        args=[edge],
        plugin_path=LIB,
        function_name="directed_edge_to_cells",
    )


def origin_to_directed_edges(cell: IntoExprColumn) -> pl.Expr:
    """
    Provides all of the directed edges from the current cell.
    """
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="origin_to_directed_edges",
    )


def directed_edge_to_boundary(edge: IntoExprColumn) -> pl.Expr:
    """
    Provides the geographic lat/lng coordinates defining the directed edge. Note that this may be more than two points for complex edges.
    """
    return register_plugin_function(
        args=[edge],
        plugin_path=LIB,
        function_name="directed_edge_to_boundary",
    )
