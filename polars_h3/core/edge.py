from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl
from polars.plugins import register_plugin_function

if TYPE_CHECKING:
    from polars_h3.typing import IntoExprColumn


LIB = Path(__file__).parent.parent


def are_neighbor_cells(origin: IntoExprColumn, destination: IntoExprColumn) -> pl.Expr:
    """
    Determine whether two H3 cells are neighbors.

    Neighboring cells share an edge. This function checks if `origin` and `destination` cells are directly adjacent at the given resolution level.

    #### Parameters
    - `origin`: IntoExprColumn
        Column or expression containing the H3 cell index serving as the origin (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
    - `destination`: IntoExprColumn
        Column or expression containing the H3 cell index serving as the destination (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

    #### Returns
    Expr
        A boolean expression evaluating to `True` if the cells are neighbors, `False` otherwise.

    #### Examples
    ```python
    >>> df = pl.DataFrame({
    ...     "cell1": [599686042433355775],
    ...     "cell2": [599686030622195711],
    ... })
    >>> df.with_columns(neighbors=polars_h3.are_neighbor_cells("cell1", "cell2"))
    shape: (1, 3)
    ┌─────────────────────┬─────────────────────┬───────────┐
    │ cell1               │ cell2               │ neighbors │
    │ ---                 │ ---                 │ ---       │
    │ u64                 │ u64                 │ bool      │
    ╞═════════════════════╪═════════════════════╪═══════════╡
    │ 599686042433355775 │ 599686030622195711 │ true      │
    └─────────────────────┴─────────────────────┴───────────┘
    ```

    #### Errors
    - `ComputeError`: If invalid cell indices are provided.
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
    Create a directed H3 edge from two neighboring cells.

    Given an origin and a destination cell, this function returns th corresponding directed edge H3 index. Directed edges represent a single edge in the H3 grid with a direction attached.

    #### Parameters
    - `origin`: IntoExprColumn
        Column or expression with the H3 cell index acting as the start of the directed edge.
    - `destination`: IntoExprColumn
        Column or expression with the H3 cell index acting as the end of the directed edge.

    #### Returns
    Expr
        Expression returning the H3 directed edge index.

    #### Examples
    ```python
    >>> df = pl.DataFrame({
    ...     "origin": [599686042433355775],
    ...     "destination": [599686030622195711],
    ... })
    >>> df.with_columns(edge=polars_h3.cells_to_directed_edge("origin", "destination"))
    shape: (1, 3)
    ┌─────────────────────┬─────────────────────┬─────────────────────┐
    │ origin              │ destination         │ edge                │
    │ ---                 │ ---                 │ ---                 │
    │ u64                 │ u64                 │ u64                 │
    ╞═════════════════════╪═════════════════════╪═════════════════════╡
    │ 599686042433355775 │ 599686030622195711 │ 1608492358964346879 │
    └─────────────────────┴─────────────────────┴─────────────────────┘
    ```

    #### Errors
    - `ComputeError`: If the cells are not neighbors or invalid.
    """
    return register_plugin_function(
        args=[origin, destination],
        plugin_path=LIB,
        function_name="cells_to_directed_edge",
    )


def is_valid_directed_edge(edge: IntoExprColumn) -> pl.Expr:
    """
    Check if an H3 index is a valid directed edge.

    #### Parameters
    - `edge`: IntoExprColumn
        Column or expression with the H3 index to validate.

    #### Returns
    Expr
        Boolean expression evaluating to `True` if `edge` is a valid directed edge, `False` otherwise.

    #### Examples
    ```python
    >>> df = pl.DataFrame({"edge": ["115283473fffffff"]})
    >>> df.with_columns(valid=polars_h3.is_valid_directed_edge("edge"))
    shape: (1, 2)
    ┌───────────────────────┬──────────┐
    │ edge                  │ valid    │
    │ ---                   │ ---      │
    │ str                   │ bool     │
    ╞═══════════════════════╪══════════╡
    │ 115283473fffffff      │ true     │
    └───────────────────────┴──────────┘
    ```

    #### Errors
    - `ComputeError`: If the input is invalid.
    """
    return register_plugin_function(
        args=[edge],
        plugin_path=LIB,
        function_name="is_valid_directed_edge",
    )


def get_directed_edge_origin(edge: IntoExprColumn) -> pl.Expr:
    """
    Extract the origin cell from a directed H3 edge.

    #### Parameters
    - `edge`: IntoExprColumn
        Column or expression with the H3 directed edge index.

    #### Returns
    Expr
        Expression returning the origin cell of the directed edge (as UInt64 or Utf8).

    #### Examples
    ```python
    >>> df = pl.DataFrame({"edge": [1608492358964346879]})
    >>> df.with_columns(origin=polars_h3.get_directed_edge_origin("edge"))
    shape: (1, 2)
    ┌─────────────────────┬─────────────────────┐
    │ edge                │ origin              │
    │ ---                 │ ---                 │
    │ u64                 │ u64                 │
    ╞═════════════════════╪═════════════════════╡
    │ 1608492358964346879 │ 599686042433355775 │
    └─────────────────────┴─────────────────────┘
    ```

    #### Errors
    - `ComputeError`: If `edge` is invalid or null.
    """
    return register_plugin_function(
        args=[edge],
        plugin_path=LIB,
        function_name="get_directed_edge_origin",
    )


def get_directed_edge_destination(edge: IntoExprColumn) -> pl.Expr:
    """
    Extract the destination cell from a directed H3 edge.

    #### Parameters
    - `edge`: IntoExprColumn
        Column or expression with the H3 directed edge index.

    #### Returns
    Expr
        Expression returning the destination cell of the directed edge (as UInt64 or Utf8).

    #### Examples
    ```python
    >>> df = pl.DataFrame({"edge": [1608492358964346879]})
    >>> df.with_columns(destination=polars_h3.get_directed_edge_destination("edge"))
    shape: (1, 2)
    ┌─────────────────────┬─────────────────────┐
    │ edge                │ destination         │
    │ ---                 │ ---                 │
    │ u64                 │ u64                 │
    ╞═════════════════════╪═════════════════════╡
    │ 1608492358964346879 │ 599686030622195711 │
    └─────────────────────┴─────────────────────┘
    ```

    #### Errors
    - `ComputeError`: If `edge` is invalid or null.
    """
    return register_plugin_function(
        args=[edge],
        plugin_path=LIB,
        function_name="get_directed_edge_destination",
    )


def directed_edge_to_cells(edge: IntoExprColumn) -> pl.Expr:
    """
    Retrieve the origin-destination cell pair from a directed edge.

    Converts a directed H3 edge back into its constituent cells. Returns a list of two cells representing [origin, destination].

    #### Parameters
    - `edge`: IntoExprColumn
        Column or expression with the H3 directed edge index.

    #### Returns
    Expr
        Expression returning a list of two cells [origin, destination].

    #### Examples
    ```python
    >>> df = pl.DataFrame({"edge": [1608492358964346879]})
    >>> df.with_columns(cells=polars_h3.directed_edge_to_cells("edge"))
    shape: (1, 2)
    ┌─────────────────────┬─────────────────────┐
    │ edge                │ cells               │
    │ ---                 │ ---                 │
    │ u64                 │ list[u64]           │
    ╞═════════════════════╪═════════════════════╡
    │ 1608492358964346879 │ [599686042433355775,… │
    └─────────────────────┴─────────────────────┘
    ```

    #### Errors
    - `ComputeError`: If `edge` is invalid or null.
    """
    return register_plugin_function(
        args=[edge],
        plugin_path=LIB,
        function_name="directed_edge_to_cells",
    )


def origin_to_directed_edges(cell: IntoExprColumn) -> pl.Expr:
    """
    List all directed edges originating from a given cell.

    Each H3 cell typically has multiple edges associated with it (6 for hexagonal cells). This function returns a list of directed edges that start from the given `origin` cell.

    #### Parameters
    - `cell`: IntoExprColumn
        Column or expression containing the H3 cell index serving as the origin.

    #### Returns
    Expr
        Expression returning a list of directed edges (UInt64 or Utf8).

    #### Examples
    ```python
    >>> df = pl.DataFrame({"h3_cell": [599686042433355775]})
    >>> df.with_columns(edges=polars_h3.origin_to_directed_edges("h3_cell"))
    shape: (1, 2)
    ┌─────────────────────┬─────────────────────────────────┐
    │ h3_cell             │ edges                           │
    │ ---                 │ ---                             │
    │ u64                 │ list[u64]                       │
    ╞═════════════════════╪═════════════════════════════════╡
    │ 599686042433355775 │ [1608492358964346879,…]          │
    └─────────────────────┴─────────────────────────────────┘
    ```

    #### Errors
    - `ComputeError`: If `cell` is invalid or null.
    """
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="origin_to_directed_edges",
    )


def directed_edge_to_boundary(edge: IntoExprColumn) -> pl.Expr:
    """
    Retrieve the geographic boundary (list of lat/lng pairs) defining a directed edge.

    Some directed edges may correspond to complex boundaries, meaning there can be more than two points defining them.

    #### Parameters
    - `edge`: IntoExprColumn
        Column or expression with the H3 directed edge index.

    #### Returns
    Expr
        Expression returning a list of lat/lng pairs representing the polygonal boundary of the edge.

    #### Examples
    ```python
    >>> df = pl.DataFrame({"edge": [1608492358964346879]})
    >>> df.with_columns(boundary=polars_h3.directed_edge_to_boundary("edge"))
    shape: (1, 2)
    ┌─────────────────────┬───────────────────────────────┐
    │ edge                │ boundary                      │
    │ ---                 │ ---                           │
    │ u64                 │ list[list[f64]]               │
    ╞═════════════════════╪═══════════════════════════════╡
    │ 1608492358964346879 │ [[37.3457, -121.9763], … ]    │
    └─────────────────────┴───────────────────────────────┘
    ```

    #### Errors
    - `ComputeError`: If `edge` is invalid, null, or its boundary cannot be computed.
    """
    return register_plugin_function(
        args=[edge],
        plugin_path=LIB,
        function_name="directed_edge_to_boundary",
    )
