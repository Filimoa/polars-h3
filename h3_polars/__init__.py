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
