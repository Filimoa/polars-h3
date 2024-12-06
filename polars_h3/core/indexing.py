from __future__ import annotations

from typing import TYPE_CHECKING
from pathlib import Path

import polars as pl
from polars.plugins import register_plugin_function
from .utils import _assert_valid_resolution, HexResolution


if TYPE_CHECKING:
    from polars_h3.typing import IntoExprColumn


LIB = Path(__file__).parent.parent


def latlng_to_cell(
    lat: IntoExprColumn, lng: IntoExprColumn, resolution: HexResolution
) -> pl.Expr:
    """
    Indexes the location at the specified resolution, providing the index of the cell containing the location. This buckets the geographic point into the H3 grid.
    """
    _assert_valid_resolution(resolution)
    return register_plugin_function(
        args=[lat, lng],
        plugin_path=LIB,
        function_name="latlng_to_cell",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def latlng_to_cell_string(
    lat: IntoExprColumn, lng: IntoExprColumn, resolution: HexResolution
) -> pl.Expr:
    """
    Indexes the location at the specified resolution, providing the index of the cell containing the location. This buckets the geographic point into the H3 grid.
    """
    _assert_valid_resolution(resolution)
    return register_plugin_function(
        args=[lat, lng],
        plugin_path=LIB,
        function_name="latlng_to_cell_string",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def cell_to_lat(cell: IntoExprColumn) -> pl.Expr:
    """
    Converts the cell index to the latitude of the cell's center.
    """
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_lat",
        is_elementwise=True,
    )


def cell_to_lng(cell: IntoExprColumn) -> pl.Expr:
    """
    Converts the cell index to the longitude of the cell's center.
    """
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_lng",
        is_elementwise=True,
    )


def cell_to_latlng(cell: IntoExprColumn) -> pl.Expr:
    """
    Finds the center of the cell in grid space. See the algorithm description for more information.

    The center will drift versus the centroid of the cell on Earth due to distortion from the gnomonic projection within the icosahedron face it resides on and its distance from the center of the icosahedron face.
    """
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_latlng",
        is_elementwise=True,
    )


def cell_to_local_ij(cell: IntoExprColumn, origin: IntoExprColumn) -> pl.Expr:
    """
    Converts the cell index to the local IJ coordinates.
    """
    return register_plugin_function(
        args=[cell, origin],
        plugin_path=LIB,
        function_name="cell_to_local_ij",
    )


def local_ij_to_cell(
    origin: IntoExprColumn, i: IntoExprColumn, j: IntoExprColumn
) -> pl.Expr:
    """
    Converts the local IJ coordinates to the cell index.
    """
    return register_plugin_function(
        args=[origin, i, j],
        plugin_path=LIB,
        function_name="local_ij_to_cell",
    )
