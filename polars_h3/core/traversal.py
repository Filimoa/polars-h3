from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl
from polars.plugins import register_plugin_function

if TYPE_CHECKING:
    from polars_h3.typing import IntoExprColumn


LIB = Path(__file__).parent.parent


def grid_distance(origin: IntoExprColumn, destination: IntoExprColumn) -> pl.Expr:
    """
    Compute the grid distance between two H3 cells.

    The grid distance is the minimum number of steps ("hops") needed to move from `origin` to `destination` by traversing neighboring cells. Note, the exact path may change slightly between library versions due to h3o.

    #### Parameters
    - `origin`: IntoExprColumn
        Column or expression with the origin H3 cell index (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
    - `destination`: IntoExprColumn
        Column or expression with the destination H3 cell index (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

    #### Returns
    Expr
        Expression returning the grid distance as an integer, or `None` if it
        cannot be computed.

    #### Examples
    ```python
    >>> df = pl.DataFrame({
    ...     "start": [605035864166236159],
    ...     "end": [605034941150920703],
    ... })
    >>> df.select(polars_h3.grid_distance("start", "end"))
    shape: (1, 1)
    ┌─────────────┐
    │ grid_distance│
    │ ---          │
    │ i64          │
    ╞══════════════╡
    │ 5            │
    └─────────────┘
    ```

    #### Errors
    - `ComputeError`: If inputs are invalid (e.g. different resolutions or pentagon issues).
    - Returns `None`: If no valid distance can be computed.
    """
    return register_plugin_function(
        args=[origin, destination],
        plugin_path=LIB,
        function_name="grid_distance",
    )


def grid_ring(cell: IntoExprColumn, k: IntoExprColumn | int) -> pl.Expr:
    """
    Produce a "hollow ring" of cells at exactly grid distance `k` from the origin cell.

    For `k=0`, this returns just the origin cell.
    For `k>0`, it returns all cells that are exactly `k` steps away.

    This function may return None items if pentagonal distortion is encountered.

    #### Parameters
    - `cell`: IntoExprColumn
        Column or expression with the H3 cell index (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
    - `k`: IntoExprColumn | int
        The ring distance. Must be non-negative.

    #### Returns
    Expr
        Expression returning a list of H3 cells at distance `k`. May return `None` if pentagonal distortion is encountered.

    #### Examples
    ```python
    >>> df = pl.DataFrame({"input": [622054503267303423]})
    >>> df.select(polars_h3.grid_ring("input", 1))
    shape: (1, 1)
    ┌───────────────────────────────────┐
    │ grid_ring                         │
    │ ---                               │
    │ list[u64]                         │
    ╞═══════════════════════════════════╡
    │ [622054502770606079, 622054502770…]│
    └───────────────────────────────────┘
    ```

    #### Errors
    - `ValueError`: If `k < 0`.
    - `ComputeError`: If pentagonal distortion or invalid inputs prevent computation.
    """
    if isinstance(k, int):
        if k < 0:
            raise ValueError("k must be non-negative")
        k_expr = pl.lit(k)
    else:
        k_expr = k
    return register_plugin_function(
        args=[cell, k_expr],
        plugin_path=LIB,
        function_name="grid_ring",
    )


def grid_disk(cell: IntoExprColumn, k: IntoExprColumn | int) -> pl.Expr:
    """
    Produce a "filled-in disk" of cells within grid distance `k` of the origin cell.

    This includes the origin cell (distance 0) and all cells up to distance `k`.
    The returned list's order is not guaranteed.

    If pentagonal distortion is encountered, this function may return None items.

    #### Parameters
    - `cell`: IntoExprColumn
        Column or expression with the H3 cell index (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
    - `k`: IntoExprColumn | int
        The maximum distance from the origin. Must be non-negative.

    #### Returns
    Expr
        Expression returning a list of H3 cells representing all cells within distance `k`.

    #### Examples
    ```python
    >>> df = pl.DataFrame({"input": [622054503267303423]})
    >>> df.select(polars_h3.grid_disk("input", 1))
    shape: (1, 1)
    ┌───────────────────────────────────┐
    │ grid_disk                         │
    │ ---                               │
    │ list[u64]                         │
    ╞═══════════════════════════════════╡
    │ [622054503267303423, 622054502770…]│
    └───────────────────────────────────┘
    ```

    #### Errors
    - `ValueError`: If `k < 0`.
    - `ComputeError`: If pentagonal distortion or invalid inputs prevent computation.
    """
    if isinstance(k, int):
        if k < 0:
            raise ValueError("k must be non-negative")
        k_expr = pl.lit(k)
    else:
        k_expr = k
    return register_plugin_function(
        args=[cell, k_expr],
        plugin_path=LIB,
        function_name="grid_disk",
    )


def grid_path_cells(origin: IntoExprColumn, destination: IntoExprColumn) -> pl.Expr:
    """
    Find a minimal contiguous path of cells from `origin` to `destination`.

    The path includes the starting and ending cells. Each cell in the path is a neighbor
    of the previous cell.

    This function may fail (return None) if:
    - The cells are extremely far apart.
    - The cells lie across a pentagonal distortion.
    - The resolution or input values are invalid.

    #### Parameters
    - `origin`: IntoExprColumn
        Column or expression with the start H3 cell index.
    - `destination`: IntoExprColumn
        Column or expression with the end H3 cell index.

    #### Returns
    Expr
        Expression returning a list of H3 cells forming a minimal path, or None if not possible.

    #### Examples
    ```python
    >>> df = pl.DataFrame({
    ...     "start": [605035864166236159],
    ...     "end": [605034941150920703],
    ... })
    >>> df.select(polars_h3.grid_path_cells("start", "end"))
    shape: (1, 1)
    ┌───────────────────────────────────┐
    │ grid_path_cells                   │
    │ ---                               │
    │ list[u64]                         │
    ╞═══════════════════════════════════╡
    │ [605035864166236159, 605035861750…]│
    └───────────────────────────────────┘
    ```

    #### Errors
    - `ComputeError`: If no valid path can be computed, due to invalid inputs or pentagon issues.
    """
    return register_plugin_function(
        args=[origin, destination],
        plugin_path=LIB,
        function_name="grid_path_cells",
    )
