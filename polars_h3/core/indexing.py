from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Union

import polars as pl
from polars.plugins import register_plugin_function

from .utils import HexResolution, assert_valid_resolution

if TYPE_CHECKING:
    from polars_h3.typing import IntoExprColumn


LIB = Path(__file__).parent.parent


def latlng_to_cell(
    lat: IntoExprColumn,
    lng: IntoExprColumn,
    resolution: HexResolution,
    return_dtype: Union[type[pl.Utf8], type[pl.UInt64], type[pl.Int64]] = pl.UInt64,
) -> pl.Expr:
    """
    Convert latitude/longitude coordinates to H3 cell indices.

    #### Parameters
    - `lat_col`: str
        - Name of the column containing latitude values (as `pl.Float64`)
    - `lng_col`: str
        - Name of the column containing longitude values (as `pl.Float64`)
    - `resolution`: int (0-15)
        - H3 resolution level
    - `return_dtype`: polars.DataType
        - Return type for the H3 indices. `pl.UInt64`, `pl.Int64`, or `pl.Utf8`

    #### Returns
    Expr
        Expression containing H3 cell indices in the specified format.

    #### Examples
    ```python
    >>> df = pl.DataFrame({
    ...     "lat": [37.7752702151959],
    ...     "lng": [-122.418307270836]
    ... })
    >>> df.with_columns(
    ...     h3_cell=polars_h3.latlng_to_cell(
    ...         "lat", "lng",
    ...         resolution=9,
    ...         return_dtype=pl.Utf8
    ...     )
    ... )
    shape: (1, 3)
    ┌──────────────────┬────────────────────┬──────────────────┐
    │ lat             │ lng                │ h3_cell          │
    │ ---             │ ---                │ ---              │
    │ f64             │ f64                │ str              │
    ╞══════════════════╪════════════════════╪══════════════════╡
    │ 37.7752702151959│ -122.418307270836  │ 8928308280fffff │
    └──────────────────┴────────────────────┴──────────────────┘

    >>> # Using integer output
    >>> df.with_columns(
    ...     h3_cell=polars_h3.latlng_to_cell(
    ...         "lat", "lng",
    ...         resolution=1,
    ...         return_dtype=pl.UInt64
    ...     )
    ... )
    shape: (1, 3)
    ┌─────────┬──────────┬─────────────────────┐
    │ lat     │ lng      │ h3_cell             │
    │ ---     │ ---      │ ---                 │
    │ f64     │ f64      │ u64                 │
    ╞═════════╪══════════╪═════════════════════╡
    │ 0.0     │ 0.0      │ 583031433791012863  │
    └─────────┴──────────┴─────────────────────┘
    ```

    #### Errors
    - `ValueError`: If resolution is invalid (must be between 0 and 15)
    - `ComputeError`: If input coordinates contain null values
    """
    assert_valid_resolution(resolution)

    if return_dtype == pl.Utf8:
        expr = register_plugin_function(
            args=[lat, lng],
            plugin_path=LIB,
            function_name="latlng_to_cell_string",
            is_elementwise=True,
            kwargs={"resolution": resolution},
        )
    else:
        expr = register_plugin_function(
            args=[lat, lng],
            plugin_path=LIB,
            function_name="latlng_to_cell",
            is_elementwise=True,
            kwargs={"resolution": resolution},
        )
        if return_dtype != pl.UInt64:
            expr = expr.cast(return_dtype)

    return expr


def cell_to_lat(cell: IntoExprColumn) -> pl.Expr:
    """
    Extract the latitude coordinate from H3 cell indices.

    #### Parameters
    - `cell`: IntoExprColumn
        Column or expression containing H3 cell indices (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

    #### Returns
    Expr
        Expression containing latitude values as `Float64`

    #### Examples
    ```python
    >>> df = pl.DataFrame({
    ...     "h3_cell": ["85283473fffffff"]
    ... })
    >>> df.with_columns(
    ...     lat=polars_h3.cell_to_lat("h3_cell"),
    ...     lng=polars_h3.cell_to_lng("h3_cell")
    ... )
    shape: (1, 3)
    ┌──────────────────┬─────────────────┬───────────────────┐
    │ h3_cell         │ lat             │ lng               │
    │ ---             │ ---             │ ---               │
    │ str             │ f64             │ f64               │
    ╞══════════════════╪═════════════════╪═══════════════════╡
    │ 85283473fffffff │ 37.345793375368 │ -121.976375972551 │
    └──────────────────┴─────────────────┴───────────────────┘

    >>> # Works with integer representation too
    >>> df = pl.DataFrame({
    ...     "h3_cell": [599686042433355775]
    ... }, schema={"h3_cell": pl.UInt64})
    >>> df.with_columns(
    ...     lat=polars_h3.cell_to_lat("h3_cell"),
    ...     lng=polars_h3.cell_to_lng("h3_cell")
    ... )
    shape: (1, 3)
    ┌─────────────────────┬─────────────────┬───────────────────┐
    │ h3_cell            │ lat             │ lng               │
    │ ---                │ ---             │ ---               │
    │ u64                │ f64             │ f64               │
    ╞═════════════════════╪═════════════════╪═══════════════════╡
    │ 599686042433355775 │ 37.345793375368 │ -121.976375972551 │
    └─────────────────────┴─────────────────┴───────────────────┘
    """
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_lat",
        is_elementwise=True,
    )


def cell_to_lng(cell: IntoExprColumn) -> pl.Expr:
    """
    Extract the longitude coordinate from H3 cell indices.

    #### Parameters
    - `cell`: IntoExprColumn
        Column or expression containing H3 cell indices (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

    #### Returns
    Expr
        Expression containing longitude values as `Float64`

    #### Examples
    ```python
    >>> df = pl.DataFrame({
    ...     "h3_cell": ["85283473fffffff"]
    ... })
    >>> df.with_columns(
    ...     lat=polars_h3.cell_to_lat("h3_cell"),
    ...     lng=polars_h3.cell_to_lng("h3_cell")
    ... )
    shape: (1, 3)
    ┌──────────────────┬─────────────────┬───────────────────┐
    │ h3_cell         │ lat             │ lng               │
    │ ---             │ ---             │ ---               │
    │ str             │ f64             │ f64               │
    ╞══════════════════╪═════════════════╪═══════════════════╡
    │ 85283473fffffff │ 37.345793375368 │ -121.976375972551 │
    └──────────────────┴─────────────────┴───────────────────┘

    >>> # Works with integer representation too
    >>> df = pl.DataFrame({
    ...     "h3_cell": [599686042433355775]
    ... }, schema={"h3_cell": pl.UInt64})
    >>> df.with_columns(
    ...     lat=polars_h3.cell_to_lat("h3_cell"),
    ...     lng=polars_h3.cell_to_lng("h3_cell")
    ... )
    shape: (1, 3)
    ┌─────────────────────┬─────────────────┬───────────────────┐
    │ h3_cell            │ lat             │ lng               │
    │ ---                │ ---             │ ---               │
    │ u64                │ f64             │ f64               │
    ╞═════════════════════╪═════════════════╪═══════════════════╡
    │ 599686042433355775 │ 37.345793375368 │ -121.976375972551 │
    └─────────────────────┴─────────────────┴───────────────────┘
    """
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_lng",
        is_elementwise=True,
    )


def cell_to_latlng(cell: IntoExprColumn) -> pl.Expr:
    """
    Convert H3 cells into a list of [latitude, longitude].

    #### Parameters
    - `cell`: IntoExprColumn
        Column or expression containing H3 cell indices (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

    #### Returns
    -------
    Expr
        Expression returning a list of floats: [lat, lng] for each H3 cell.

    Raises
    ------
    ComputeError
        If null or invalid H3 cell indices are encountered.

    Examples
    --------
    Retrieve both latitude and longitude as a single list:

    >>> df = pl.DataFrame({
    ...     "cell": ["85283473fffffff"]
    ... })
    >>> df.select(polars_h3.cell_to_latlng("cell"))
    shape: (1, 1)
    ┌─────────────────────────┐
    │ cell_to_latlng          │
    │ ---                     │
    │ list[f64]               │
    ╞═════════════════════════╡
    │ [37.3457934, -121.9763…]│
    └─────────────────────────┘

    From there, you could easily extract latitude/longitude as separate columns:
    >>> df.select([
    ...     polars_h3.cell_to_latlng("cell").arr.get(0).alias("lat"),
    ...     polars_h3.cell_to_latlng("cell").arr.get(1).alias("lng"),
    ... ])
    shape: (1, 2)
    ┌───────────┬───────────┐
    │ lat       │ lng       │
    │ ---       │ ---       │
    │ f64       │ f64       │
    ╞═══════════╡═══════════╡
    │ 37.345793…│ -121.9763…│
    └───────────┴───────────┘
    """
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_latlng",
        is_elementwise=True,
    )


def cell_to_local_ij(cell: IntoExprColumn, origin: IntoExprColumn) -> pl.Expr:
    """
    Convert an H3 cell index into its local IJ coordinates relative to a given origin.

    The local IJ coordinate system is a two-dimensional coordinate system that represents H3 cells relative to a specified origin cell. This can be useful for certain types of indexing, grid navigation, or computing distances in a planar, local context.

    #### Parameters
    - `cell`: IntoExprColumn
        Column or expression containing the H3 cell index to convert (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
    - `origin`: IntoExprColumn
        Expression or column name containing the H3 cell index considered as the origin point.

    Returns
    -------
    Expr
        Expression returning a list or struct of integers [i, j] representing the local IJ coordinates.

    Raises
    ------
    ComputeError
        If the `cell` or `origin` values are null, invalid, or cannot be converted.

    Examples
    --------
    Given a DataFrame with `origin` and `cell` columns containing H3 cell indices,
    find their local IJ coordinates:

    >>> df = pl.DataFrame({
    ...     "origin": [599686042433355775],
    ...     "cell": [599686042433355776]
    ... })
    >>> df.select(polars_h3.cell_to_local_ij("cell", "origin"))
    shape: (1, 1)
    ┌────────────────┐
    │ cell_to_local_ij│
    │ ---            │
    │ list[i64]      │
    ╞════════════════╡
    │ [0,1]          │
    └────────────────┘
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
    Convert local IJ coordinates back into an H3 cell index using a given origin.

    This function performs the inverse operation of `cell_to_local_ij`. Given a local IJ coordinate pair `[i, j]` relative to an `origin` cell, it returns the corresponding H3 cell index in the global coordinate system.

    #### Parameters
    - `origin`: IntoExprColumn
        Column or expression containing the H3 origin cell index that defines
        the local IJ space.
    - `i`: IntoExprColumn
        Expression or column name representing the i-coordinate (row) in the local IJ system.
    - `j`: IntoExprColumn
        Expression or column name representing the j-coordinate (column) in the local IJ system.

    #### Returns
    -------
    Expr
        Expression returning the H3 cell index corresponding to the local [i, j] coordinates.

    Raises
    ------
    ComputeError
        If null or invalid inputs are encountered, or if the transformation cannot be performed.

    Examples
    --------
    Given an origin cell and local coordinates [0, 1], find the corresponding H3 cell:

    >>> df = pl.DataFrame({
    ...     "origin": [599686042433355775],
    ...     "i": [0],
    ...     "j": [1]
    ... })
    >>> df.select(polars_h3.local_ij_to_cell("origin", "i", "j"))
    shape: (1, 1)
    ┌─────────────────┐
    │ local_ij_to_cell │
    │ ---             │
    │ u64             │
    ╞═════════════════╡
    │ 599686042433355776 │
    └─────────────────┘
    """
    return register_plugin_function(
        args=[origin, i, j],
        plugin_path=LIB,
        function_name="local_ij_to_cell",
    )


def cell_to_boundary(cell: IntoExprColumn) -> pl.Expr:
    """
    Retrieve the polygon boundary coordinates of the given H3 cell.

    This function computes the vertices of the H3 cell's polygon boundary and returns them as a list of alternating latitude and longitude values. The coordinate list is structured as: `[lat0, lng0, lat1, lng1, ..., latN, lngN]`.

    #### Parameters
    - `cell`: IntoExprColumn
        Column or expression containing H3 cell indices (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

    #### Returns
    Expr
        A `pl.Expr` returning a list of `Float64` values representing the boundary vertices
        of the cell in latitude-longitude pairs.

    #### Examples
    ```python
    >>> df = pl.DataFrame({
    ...     "cell": ["8a1fb464492ffff"]
    ... })
    >>> df.select(polars_h3.cell_to_boundary("cell"))
    shape: (1, 1)
    ┌────────────────────────────────────┐
    │ cell_to_boundary                   │
    │ ---                                │
    │ list[f64]                          │
    ╞════════════════════════════════════╡
    │ [[50.99, -76.05], [48.29, -81.91...│
    └────────────────────────────────────┘

    #### Errors
    - `ComputeError`: If null or invalid H3 cell indices are encountered.
    """
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_boundary",
        is_elementwise=True,
    )
