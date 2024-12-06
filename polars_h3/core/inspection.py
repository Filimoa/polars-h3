from __future__ import annotations

from typing import TYPE_CHECKING, Union
from pathlib import Path

import polars as pl
from polars.plugins import register_plugin_function
from .utils import _assert_valid_resolution, HexResolution


if TYPE_CHECKING:
    from polars_h3.typing import IntoExprColumn


LIB = Path(__file__).parent.parent


def get_resolution(expr: IntoExprColumn) -> pl.Expr:
    """
    Returns the resolution of the index. (Works for cells, edges, and vertexes.)
    """
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="get_resolution",
        is_elementwise=True,
    )


def str_to_int(expr: IntoExprColumn) -> pl.Expr:
    """
    Converts the pl.Utf8 representation to H3Index (pl.UInt64) representation.
    """
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="str_to_int",
        is_elementwise=True,
    )


def int_to_str(expr: IntoExprColumn) -> pl.Expr:
    """
    Converts the H3Index pl.UInt64 representation to the pl.Utf8 representation.
    """
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="int_to_str",
        is_elementwise=True,
    )


def is_valid_cell(expr: IntoExprColumn) -> pl.Expr:
    """
    Checks if the cell is valid.
    """
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="is_valid_cell",
        is_elementwise=True,
    )


def is_pentagon(expr: IntoExprColumn) -> pl.Expr:
    """
    Checks if the cell is a pentagon.
    """
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="is_pentagon",
        is_elementwise=True,
    )


def is_res_class_III(expr: IntoExprColumn) -> pl.Expr:
    """
    Checks if the cell is a res_class_III cell.
    """
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="is_res_class_III",
        is_elementwise=True,
    )


def get_icosahedron_faces(expr: IntoExprColumn) -> pl.Expr:
    """
    Find all icosahedron faces intersected by a given H3 cell. Faces are represented as integers from 0-19, inclusive.
    """
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="get_icosahedron_faces",
        is_elementwise=True,
    )


def cell_to_parent(
    cell: IntoExprColumn, resolution: Union[HexResolution, None] = None
) -> pl.Expr:
    """
    Returns the parent cell at the specified resolution.
    """
    _assert_valid_resolution(resolution)
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_parent",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def cell_to_center_child(
    cell: IntoExprColumn, resolution: Union[HexResolution, None] = None
) -> pl.Expr:
    """
    Returns the center child cell at the specified resolution.
    """
    _assert_valid_resolution(resolution)
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_center_child",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def cell_to_children_size(
    cell: IntoExprColumn, resolution: Union[HexResolution, None] = None
) -> pl.Expr:
    """
    Returns the number of children cells at the specified resolution.
    """
    _assert_valid_resolution(resolution)
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_children_size",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def cell_to_children(cell: IntoExprColumn, resolution: HexResolution) -> pl.Expr:
    """
    Returns the children cells at the specified resolution.
    """
    _assert_valid_resolution(resolution)
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_children",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def cell_to_child_pos(cell: IntoExprColumn, resolution: HexResolution) -> pl.Expr:
    """
    Returns the position of the child cell in the parent cell.
    """
    _assert_valid_resolution(resolution)
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_child_pos",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def child_pos_to_cell(
    parent: IntoExprColumn, pos: IntoExprColumn, resolution: HexResolution
) -> pl.Expr:
    """
    Returns the child cell at the specified position in the parent cell.
    """
    _assert_valid_resolution(resolution)
    return register_plugin_function(
        args=[parent, pos],
        plugin_path=LIB,
        function_name="child_pos_to_cell",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def compact_cells(cells: IntoExprColumn) -> pl.Expr:
    """
    Compact a set of H3 cells into a smaller set of H3 cells.
    """
    return register_plugin_function(
        args=[cells],
        plugin_path=LIB,
        function_name="compact_cells",
        is_elementwise=True,
    )


def uncompact_cells(cells: IntoExprColumn, resolution: HexResolution) -> pl.Expr:
    """
    Uncompact a set of H3 cells into a larger set of H3 cells.
    """
    _assert_valid_resolution(resolution)
    return register_plugin_function(
        args=[cells],
        plugin_path=LIB,
        function_name="uncompact_cells",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )
