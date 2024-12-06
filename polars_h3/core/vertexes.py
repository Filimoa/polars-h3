from __future__ import annotations

from typing import TYPE_CHECKING
from pathlib import Path

import polars as pl
from polars.plugins import register_plugin_function


if TYPE_CHECKING:
    from polars_h3.typing import IntoExprColumn


LIB = Path(__file__).parent.parent


def cell_to_vertex(cell: IntoExprColumn, vertex_num: int) -> pl.Expr:
    """
    Returns the index for the specified cell vertex. Valid vertex numbers are between 0 and 5 (inclusive) for hexagonal cells, and 0 and 4 (inclusive) for pentagonal cells.
    """
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_vertex",
        kwargs={"vertex_num": vertex_num},
    )


def cell_to_vertexes(cell: IntoExprColumn) -> pl.Expr:
    """
    Returns the indexes for all vertexes of the given cell.
    """
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_vertexes",
    )


def vertex_to_latlng(vertex: IntoExprColumn) -> pl.Expr:
    """
    Returns the latitude and longitude coordinates of the given vertex.
    """
    return register_plugin_function(
        args=[vertex],
        plugin_path=LIB,
        function_name="vertex_to_latlng",
    )


def is_valid_vertex(vertex: IntoExprColumn) -> pl.Expr:
    """
    Determines if the given H3 index represents a valid H3 vertex.
    """
    return register_plugin_function(
        args=[vertex],
        plugin_path=LIB,
        function_name="is_valid_vertex",
    )
