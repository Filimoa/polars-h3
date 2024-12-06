from __future__ import annotations

from typing import TYPE_CHECKING
from pathlib import Path

import polars as pl
from polars.plugins import register_plugin_function


if TYPE_CHECKING:
    from polars_h3.typing import IntoExprColumn


LIB = Path(__file__).parent.parent

# ===== Traversal ===== #


def grid_distance(origin: IntoExprColumn, destination: IntoExprColumn) -> pl.Expr:
    """
    Provides the grid distance between two cells, which is defined as the minimum number of "hops" needed across adjacent cells to get from one cell to the other.

    Note that finding the grid distance may fail for a few reasons:

    - the cells are not comparable (different resolutions),
    - the cells are too far apart, or
    - the cells are separated by pentagonal distortion.

    This is the same set of limitations as the local IJ coordinate space functions.
    """
    return register_plugin_function(
        args=[origin, destination],
        plugin_path=LIB,
        function_name="grid_distance",
    )


def grid_ring(cell: IntoExprColumn, k: int) -> pl.Expr:
    """
    Produces the "hollow ring" of cells which are exactly grid distance k from the origin cell.

    This function may fail if pentagonal distortion is encountered.
    """
    if k < 0:
        raise ValueError("k must be non-negative")
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="grid_ring",
        kwargs={"k": k},
    )


def grid_disk(cell: IntoExprColumn, k: int) -> pl.Expr:
    """
    Produces the "filled-in disk" of cells which are at most grid distance k from the origin cell.

    Output order is not guaranteed.
    """
    if k < 0:
        raise ValueError("k must be non-negative")
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="grid_disk",
        kwargs={"k": k},
    )


def grid_path_cells(origin: IntoExprColumn, destination: IntoExprColumn) -> pl.Expr:
    """
    Given two H3 cells, return a minimal-length contiguous path of cells between them (inclusive of the endpoint cells).

    This function may fail if the cells are very far apart, or if the cells are on opposite sides of a pentagon.

    Notes:

    The output of this function should not be considered stable across library versions. The only guarantees are that the path length will be gridDistance(start, end) + 1 and that every cell in the path will be a neighbor of the preceding cell.

    Paths exist in the H3 grid of cells, and may not align closely with either Cartesian lines or great arcs.
    """
    return register_plugin_function(
        args=[origin, destination],
        plugin_path=LIB,
        function_name="grid_path_cells",
    )
