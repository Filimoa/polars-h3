from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

import polars as pl
from polars.plugins import register_plugin_function

from . import _consts

if TYPE_CHECKING:
    from polars_h3.typing import IntoExprColumn


LIB = Path(__file__).parent.parent

AreaUnit = Literal["km^2", "m^2"]
EdgeLengthUnit = Literal["km", "m"]


def _deg_to_rad(col: IntoExprColumn | str) -> pl.Expr:
    return pl.col(col) * pl.lit(3.141592653589793) / pl.lit(180)  # type: ignore


def great_circle_distance(
    s_lat_deg: IntoExprColumn,
    s_lng_deg: IntoExprColumn,
    e_lat_deg: IntoExprColumn,
    e_lng_deg: IntoExprColumn,
    unit: EdgeLengthUnit = "km",
) -> pl.Expr:
    """
    Haversine distance calculation using polars.

    The error can be up to about 0.5% on distances of 1000km, but is much smaller for smaller distances.

    #### Parameters
    - `s_lat_deg`: IntoExprColumn
        Column or expression containing the starting latitude in degrees (as `pl.Float64`).
    - `s_lng_deg`: IntoExprColumn
        Column or expression containing the starting longitude in degrees (as `pl.Float64`).
    - `e_lat_deg`: IntoExprColumn
        Column or expression containing the ending latitude in degrees (as `pl.Float64`).
    - `e_lng_deg`: IntoExprColumn
        Column or expression containing the ending longitude in degrees (as `pl.Float64`).
    - `unit`: str
        Unit of the distance. `km` or `m`.

    #### Returns
    Expr
        Expression returning the great circle distance between the two points.
    """
    EARTH_RADIUS_KM = 6373.0

    s_lat_rad = _deg_to_rad(s_lat_deg)
    s_lng_rad = _deg_to_rad(s_lng_deg)
    e_lat_rad = _deg_to_rad(e_lat_deg)
    e_lng_rad = _deg_to_rad(e_lng_deg)

    haversine_km = (
        2
        * EARTH_RADIUS_KM
        * (
            (e_lat_rad - s_lat_rad).truediv(2).sin().pow(2)
            + (s_lat_rad.cos() * e_lat_rad.cos())
            * (e_lng_rad - s_lng_rad).truediv(2).sin().pow(2)
        )
        .sqrt()
        .arcsin()
    )

    return haversine_km * pl.when(pl.lit(unit) == "m").then(pl.lit(1000)).otherwise(
        pl.lit(1)
    )


def average_hexagon_area(resolution: IntoExprColumn, unit: str = "km^2") -> pl.Expr:
    """
    Return the average area of an H3 hexagon at a given resolution.

    The H3 grid is hierarchical; as resolution increases, the hexagons become
    smaller. This function provides the average area of a hexagon cell at the specified resolution.

    #### Parameters
    - `resolution`: IntoExprColumn
        Column or expression with the H3 resolution (0 to 15).
    - `unit`: {"km^2", "m^2"}
        Unit of the returned area. Defaults to square kilometers.

    #### Returns
    Expr
        Expression returning the average area as a float.

    #### Examples
    ```python
    >>> df = pl.DataFrame({"resolution": [5]}, schema={"resolution": pl.UInt64})
    >>> df.with_columns(
    ...     area=polars_h3.average_hexagon_area("resolution", "km^2")
    ... )
    shape: (1, 2)
    ┌─────────────┬──────────┐
    │ resolution  │ area     │
    │ ---          │ ---      │
    │ u64          │ f64      │
    ╞══════════════╪══════════╡
    │ 5            │ 252.903858│
    └─────────────┴──────────┘
    ```
    """
    if unit not in ["km^2", "m^2"]:
        raise ValueError("Unit must be either 'km^2' or 'm^2'")

    resolution_expr = pl.col(resolution) if isinstance(resolution, str) else resolution
    area_m2 = resolution_expr.replace(_consts.AVG_AREA_M2)

    return pl.when(pl.lit(unit) == "km^2").then(area_m2 / 1_000_000).otherwise(area_m2)


def cell_area(cell: IntoExprColumn, unit: AreaUnit = "km^2") -> pl.Expr:
    """
    Get the area of a specific H3 cell.
    """
    if unit not in ["km^2", "m^2"]:
        raise ValueError("Unit must be either 'km^2' or 'm^2'")

    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_area",
        is_elementwise=True,
        kwargs={"unit": unit},
    )


def edge_length(cell: IntoExprColumn, unit: EdgeLengthUnit = "km") -> pl.Expr:
    """
    Determine the length of an H3 edge cell.

    For cells that represent edges (directed edges), this returns the edge length.

    #### Parameters
    - `cell`: IntoExprColumn
        Column or expression with the H3 cell index representing an edge.
    - `unit`: {"km", "m"}
        Unit of the returned length. Defaults to kilometers.

    #### Returns
    Expr
        Expression returning the edge length as a float, or `None` if invalid.

    #### Examples
    ```python
    >>> df = pl.DataFrame({"h3_cell": [1608492358964346879]}, schema={"h3_cell": pl.UInt64})
    >>> df.with_columns(length=polars_h3.edge_length("h3_cell", "km"))
    shape: (1, 2)
    ┌─────────────────────┬─────────┐
    │ h3_cell             │ length  │
    │ ---                 │ ---     │
    │ u64                 │ f64     │
    ╞═════════════════════╪═════════╡
    │ 1608492358964346879 │ 10.3029 │
    └─────────────────────┴─────────┘
    ```
    """
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="edge_length",
        is_elementwise=True,
        kwargs={"unit": unit},
    )


def average_hexagon_edge_length(
    resolution: IntoExprColumn, unit: str = "km"
) -> pl.Expr:
    """
    Get the average edge length of H3 hexagons at a specific resolution.

    Each hexagon cell at the same resolution has roughly the same edge length.
    This function provides the average edge length for a given resolution.

    #### Parameters
    - `resolution`: IntoExprColumn
        Column or expression with the H3 resolution (0 to 15).
    - `unit`: {"km", "m"}
        Unit of the returned length. Defaults to kilometers.

    #### Returns
    Expr
        Expression returning the average edge length as a float.

    #### Examples
    ```python
    >>> df = pl.DataFrame({"resolution": [1]})
    >>> df.with_columns(
    ...     length=polars_h3.average_hexagon_edge_length("resolution", "km")
    ... )
    shape: (1, 2)
    ┌─────────────┬─────────┐
    │ resolution  │ length  │
    │ ---          │ ---     │
    │ u64          │ f64     │
    ╞══════════════╪═════════╡
    │ 1            │ 418.676 │
    └─────────────┴─────────┘
    ```
    """
    if unit not in ["km", "m"]:
        raise ValueError("Unit must be either 'km' or 'm'")

    resolution_expr = pl.col(resolution) if isinstance(resolution, str) else resolution
    edge_length_m = resolution_expr.replace(_consts.AVG_EDGE_LENGTH_M)

    return (
        pl.when(pl.lit(unit) == "km")
        .then(edge_length_m / 1_000)
        .otherwise(edge_length_m)
    )


def get_num_cells(resolution: IntoExprColumn) -> pl.Expr:
    """
    Get the number of unique H3 cells at a given resolution.

    The number of cells grows significantly with resolution. This function
    returns the total count of cells for the specified resolution.

    #### Parameters
    - `resolution`: IntoExprColumn
        Column or expression with the H3 resolution (0 to 15).

    #### Returns
    Expr
        Expression returning the number of cells as an integer.

    #### Examples
    ```python
    >>> df = pl.DataFrame({"resolution": [5]}, schema={"resolution": pl.UInt64})
    >>> df.with_columns(count=polars_h3.get_num_cells("resolution"))
    shape: (1, 2)
    ┌─────────────┬──────────┐
    │ resolution  │ count    │
    │ ---          │ ---      │
    │ u64          │ i64      │
    ╞══════════════╪══════════╡
    │ 5            │ 2016842  │
    └─────────────┴──────────┘
    ```
    """

    resolution_expr = pl.col(resolution) if isinstance(resolution, str) else resolution
    return resolution_expr.cast(pl.UInt8).replace(_consts.NUM_CELLS_BY_RESOLUTION)


def get_pentagons(resolution: IntoExprColumn) -> pl.Expr:
    """
    Get the number of pentagons at a given resolution.

    #### Parameters
    - `resolution`: IntoExprColumn
        Column or expression with the H3 resolution (0 to 15).

    #### Returns
    Expr
        Expression returning the number of cells as an integer.

    #### Examples
    ```python
    >>> df = pl.DataFrame({"resolution": [5]}, schema={"resolution": pl.UInt64})
    >>> df.with_columns(count=polars_h3.get_num_cells("resolution"))
    shape: (1, 2)
    ┌─────────────┬──────────┐
    │ resolution  │ count    │
    │ ---          │ ---      │
    │ u64          │ i64      │
    ╞══════════════╪══════════╡
    │ 5            │ 2016842  │
    └─────────────┴──────────┘
    ```
    """

    return register_plugin_function(
        args=[resolution],
        plugin_path=LIB,
        function_name="get_pentagons",
        is_elementwise=True,
    )
