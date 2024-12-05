from __future__ import annotations
from typing import TYPE_CHECKING
from pathlib import Path
import polars as pl
from polars.plugins import register_plugin_function


if TYPE_CHECKING:
    from h3_polars.typing import IntoExprColumn

LIB = Path(__file__).parent


def lat_lng_to_h3(lat: IntoExprColumn, lng: IntoExprColumn) -> pl.Expr:
    return register_plugin_function(
        args=[lat, lng],
        plugin_path=LIB,
        function_name="lat_lng_to_h3",
        is_elementwise=True,
    )
