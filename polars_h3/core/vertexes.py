from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl
from polars.plugins import register_plugin_function

if TYPE_CHECKING:
    from polars_h3.typing import IntoExprColumn


LIB = Path(__file__).parent.parent


def cell_to_vertex(cell: IntoExprColumn, vertex_num: int) -> pl.Expr:
    """
    Retrieve the H3 vertex index for a specific vertex of a given cell.

    Valid vertex numbers range from 0 to 5 for hexagonal cells, and 0 to 4 for pentagonal cells. Providing an out-of-range vertex number will raise a compute error.

    #### Parameters
    - `cell`: IntoExprColumn
        Column or expression containing the H3 cell index (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
    - `vertex_num`: int
        The vertex number to extract (0-based).

    #### Returns
    Expr
        Expression returning the corresponding H3 vertex index as an integer or `None` if invalid.

    #### Examples
    ```python
    # Example using an integer H3 cell index
    >>> df = pl.DataFrame({"h3_cell": [599686042433355775]})
    >>> df.with_columns(vertex=polars_h3.cell_to_vertex("h3_cell", 0))
    shape: (1, 2)
    ┌─────────────────────┬─────────────────────┐
    │ h3_cell             │ vertex              │
    │ ---                 │ ---                 │
    │ u64                 │ u64                 │
    ╞═════════════════════╪═════════════════════╡
    │ 599686042433355775 │ 2473183459502194687 │
    └─────────────────────┴─────────────────────┘
    ```

    #### Errors
    - `ComputeError`: If `vertex_num` is out of range or the cell is invalid.
    """
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_vertex",
        kwargs={"vertex_num": vertex_num},
    )


def cell_to_vertexes(cell: IntoExprColumn) -> pl.Expr:
    """
    Retrieve all vertex indexes for a given H3 cell.

    Returns the full set of vertices defining the cell's boundary. For hexagonal cells, this will be six vertex indices; for pentagonal cells, five.

    #### Parameters
    - `cell`: IntoExprColumn
        Column or expression containing the H3 cell index (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

    #### Returns
    Expr
        Expression returning a list of H3 vertex indices, or `None` if invalid.

    #### Examples
    ```python
    >>> df = pl.DataFrame({"h3_cell": [599686042433355775]})
    >>> df.with_columns(vertexes=polars_h3.cell_to_vertexes("h3_cell"))
    shape: (1, 2)
    ┌─────────────────────┬────────────────────────────────────────────────┐
    │ h3_cell             │ vertexes                                       │
    │ ---                 │ ---                                             │
    │ u64                 │ list[u64]                                       │
    ╞═════════════════════╪════════════════════════════════════════════════╡
    │ 599686042433355775 │ [2473183459502194687, 2545241069646249983, … ] │
    └─────────────────────┴────────────────────────────────────────────────┘
    ```
    """
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_vertexes",
    )


def vertex_to_latlng(vertex: IntoExprColumn) -> pl.Expr:
    """
    Convert an H3 vertex index into its latitude and longitude coordinates.

    Given a single vertex index, this function returns a list of two floats: `[lat, lng]`,
    representing the geographic coordinates of the vertex. If the vertex is invalid, returns `None`.

    #### Parameters
    - `vertex`: IntoExprColumn
        Column or expression containing an H3 vertex index.

    #### Returns
    Expr
        Expression returning `[latitude, longitude]` as `[f64, f64]`, or `None` if invalid.

    #### Examples
    ```python
    >>> df = pl.DataFrame({"vertex": [2459626752788398079]})
    >>> df.with_columns(coords=polars_h3.vertex_to_latlng("vertex"))
    shape: (1, 2)
    ┌──────────────────────┬─────────────────────────┐
    │ vertex               │ coords                  │
    │ ---                  │ ---                     │
    │ u64                  │ list[f64]               │
    ╞══════════════════════╪═════════════════════════╡
    │ 2459626752788398079 │ [39.38084284181812, 88.57496213785487] │
    └──────────────────────┴─────────────────────────┘
    ```
    """
    return register_plugin_function(
        args=[vertex],
        plugin_path=LIB,
        function_name="vertex_to_latlng",
    )


def is_valid_vertex(vertex: IntoExprColumn) -> pl.Expr:
    """
    Check whether an H3 index represents a valid H3 vertex.

    Returns a boolean `True` if the vertex is valid, `False` otherwise.

    #### Parameters
    - `vertex`: IntoExprColumn
        Column or expression containing the H3 vertex index.

    #### Returns
    Expr
        A boolean expression indicating vertex validity.

    #### Examples
    ```python
    >>> df = pl.DataFrame({"vertex": [2459626752788398079]})
    >>> df.with_columns(valid=polars_h3.is_valid_vertex("vertex"))
    shape: (1, 2)
    ┌──────────────────────┬──────────┐
    │ vertex               │ valid    │
    │ ---                  │ ---      │
    │ u64                  │ bool     │
    ╞══════════════════════╪══════════╡
    │ 2459626752788398079 │ true     │
    └──────────────────────┴──────────┘
    ```
    """
    return register_plugin_function(
        args=[vertex],
        plugin_path=LIB,
        function_name="is_valid_vertex",
    )
