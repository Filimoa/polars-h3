from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl
from polars.plugins import register_plugin_function

from .utils import HexResolution, assert_valid_resolution

if TYPE_CHECKING:
    from polars_h3.typing import IntoExprColumn


LIB = Path(__file__).parent.parent


def get_resolution(expr: IntoExprColumn) -> pl.Expr:
    """
    Retrieve the resolution of H3 indices (cells, edges, or vertexes).

    #### Parameters
    - `expr`: IntoExprColumn
        Column or expression containing H3 cells (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

    #### Returns
    Expr
        A Polars expression yielding an integer resolution (0-15) for each H3 index.

    #### Examples
    ```python
    >>> df = pl.DataFrame({
    ...     "h3_cell": [599686042433355775]
    ... })
    >>> df.with_columns(
    ...     resolution=polars_h3.get_resolution("h3_cell")
    ... )
    shape: (1, 2)
    ┌─────────────────────┬────────────┐
    │ h3_cell             │ resolution │
    │ ---                 │ ---        │
    │ u64                 │ i64        │
    ╞═════════════════════╪════════════╡
    │ 599686042433355775  │ 2          │
    └─────────────────────┴────────────┘
    ```
    """
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="get_resolution",
        is_elementwise=True,
    )


def str_to_int(expr: IntoExprColumn) -> pl.Expr:
    """
    Convert string H3 indices into their unsigned 64-bit integer representation.

    #### Parameters
    - `expr`: IntoExprColumn
        Column or expression containing H3 cells as strings (e.g. `"85283473fffffff"`).

    #### Returns
    Expr
        A Polars expression yielding `pl.UInt64` integer H3 indices, or `None` for invalid strings.

    #### Examples
    ```python
    >>> df = pl.DataFrame({
    ...     "h3_str": ["85283473fffffff", "invalid_index"]
    ... })
    >>> df.with_columns(
    ...     h3_int=polars_h3.str_to_int("h3_str")
    ... )
    shape: (2, 2)
    ┌──────────────────┬─────────────────────┐
    │ h3_str           │ h3_int              │
    │ ---              │ ---                 │
    │ str              │ u64                 │
    ╞══════════════════╪═════════════════════╡
    │ 85283473fffffff  │ 599686042433355775  │
    │ invalid_index    │ null                │
    └──────────────────┴─────────────────────┘
    ```
    """
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="str_to_int",
        is_elementwise=True,
    )


def int_to_str(expr: IntoExprColumn) -> pl.Expr:
    """
    Convert integer H3 indices into their string representation.

    #### Parameters
    - `expr`: IntoExprColumn
        Column or expression containing H3 cells as integers (`pl.UInt64`, `pl.Int64` or `pl.Int64`).

    #### Returns
    Expr
        A Polars expression yielding string representations of H3 indices, or `None` for invalid integers.

    #### Examples
    ```python
    >>> df = pl.DataFrame({
    ...     "h3_int": [599686042433355775, -1]
    ... })
    >>> df.with_columns(
    ...     h3_str=polars_h3.int_to_str("h3_int")
    ... )
    shape: (2, 2)
    ┌─────────────────────┬──────────────────┐
    │ h3_int              │ h3_str           │
    │ ---                 │ ---              │
    │ u64                 │ str              │
    ╞═════════════════════╪══════════════════╡
    │ 599686042433355775  │ 85283473fffffff  │
    │ -1                  │ null             │
    └─────────────────────┴──────────────────┘
    ```
    """
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="int_to_str",
        is_elementwise=True,
    )


def is_valid_cell(expr: IntoExprColumn) -> pl.Expr:
    """
    Check if H3 cell indices are valid.

    #### Parameters
    - `expr`: IntoExprColumn
        Column or expression containing H3 cells (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

    #### Returns
    Expr
        A Polars boolean expression, `True` if valid, `False` otherwise.

    #### Examples
    ```python
    >>> df = pl.DataFrame({
    ...     "h3_cell": ["85283473fffffff", "invalid_cell"]
    ... })
    >>> df.with_columns(
    ...     valid=polars_h3.is_valid_cell("h3_cell")
    ... )
    shape: (3, 2)
    ┌─────────────────────┬───────┐
    │ h3_cell             │ valid │
    │ ---                 │ ---   │
    │ str                 │ bool  │
    ╞═════════════════════╪═══════╡
    │ 85283473fffffff     │ true  │
    │ invalid_cell        │ false │
    └─────────────────────┴───────┘
    ```
    """
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="is_valid_cell",
        is_elementwise=True,
    )


def is_pentagon(expr: IntoExprColumn) -> pl.Expr:
    """
    Determine if H3 cells are pentagons.

    #### Parameters
    - `expr`: IntoExprColumn
        H3 cells as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`.

    #### Returns
    Expr
        Boolean expression indicating if each H3 cell is a pentagon.

    #### Examples
    ```python
    >>> df = pl.DataFrame({
    ...     "h3_cell": [585961082523222015, 599686042433355775]
    ... })
    >>> df.with_columns(
    ...     is_pent=polars_h3.is_pentagon("h3_cell")
    ... )
    shape: (2, 2)
    ┌─────────────────────┬─────────┐
    │ h3_cell             │ is_pent │
    │ ---                 │ ---     │
    │ u64                 │ bool    │
    ╞═════════════════════╪═════════╡
    │ 585961082523222015  │ true    │
    │ 599686042433355775  │ false   │
    └─────────────────────┴─────────┘
    ```
    """
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="is_pentagon",
        is_elementwise=True,
    )


def is_res_class_III(expr: IntoExprColumn) -> pl.Expr:
    """
    Check if H3 cells belong to the Class III resolution set.

    #### Parameters
    - `expr`: IntoExprColumn
        H3 cells (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

    #### Returns
    Expr
        Boolean expression indicating if each cell is Class III.

    #### Examples
    ```python
    >>> df = pl.DataFrame({
    ...     "h3_cell": [582692784209657855, 586265647244115967]
    ... })
    >>> df.with_columns(
    ...     is_class_3=polars_h3.is_res_class_III("h3_cell")
    ... )
    shape: (2, 2)
    ┌─────────────────────┬────────────┐
    │ h3_cell             │ is_class_3 │
    │ ---                 │ ---        │
    │ u64                 │ bool       │
    ╞═════════════════════╪════════════╡
    │ 582692784209657855  │ true       │
    │ 586265647244115967  │ false      │
    └─────────────────────┴────────────┘
    ```
    """
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="is_res_class_III",
        is_elementwise=True,
    )


def get_icosahedron_faces(expr: IntoExprColumn) -> pl.Expr:
    """
    Retrieve the icosahedron faces intersected by an H3 cell.

    #### Parameters
    - `expr`: IntoExprColumn
        H3 cells as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`.

    #### Returns
    Expr
        List of intersected icosahedron face indices.

    #### Examples
    ```python
    >>> df = pl.DataFrame({
    ...     "h3_cell": [599686042433355775]
    ... })
    >>> df.with_columns(
    ...     faces=polars_h3.get_icosahedron_faces("h3_cell")
    ... )
    shape: (1, 2)
    ┌─────────────────────┬─────────┐
    │ h3_cell             │ faces   │
    │ ---                 │ ---     │
    │ u64                 │ list[i64]│
    ╞═════════════════════╪═════════╡
    │ 599686042433355775  │ [7]     │
    └─────────────────────┴─────────┘
    ```
    """
    return register_plugin_function(
        args=[expr],
        plugin_path=LIB,
        function_name="get_icosahedron_faces",
        is_elementwise=True,
    )


def cell_to_parent(
    cell: IntoExprColumn,
    resolution: HexResolution,
) -> pl.Expr:
    """
    Retrieve the parent cell of a given H3 cell at a specified resolution.

    #### Parameters
    - `cell`: IntoExprColumn
        H3 cells as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`.
    - `resolution`: int (0-15)
        Target parent resolution.

    #### Returns
    Expr
        The parent cell at the given resolution (`pl.UInt64`, `pl.Int64`, or `pl.Utf8` depending on your indexing).

    #### Examples
    ```python
    >>> df = pl.DataFrame({"h3_cell": [599686042433355775]})
    >>> df.with_columns(
    ...     parent=polars_h3.cell_to_parent("h3_cell", 1)
    ... )
    ```
    """
    assert_valid_resolution(resolution)
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_parent",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def cell_to_center_child(cell: IntoExprColumn, resolution: HexResolution) -> pl.Expr:
    """
    Retrieve the center child cell of an H3 cell at a specified resolution.

    #### Parameters
    - `cell`: IntoExprColumn
        H3 cells as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`.
    - `resolution`: int (0-15)
        Target resolution for the center child.

    #### Returns
    Expr
        The center child cell at the given resolution.

    #### Examples
    ```python
    >>> df = pl.DataFrame({"h3_cell": [582692784209657855]})
    >>> df.with_columns(
    ...     center_child=polars_h3.cell_to_center_child("h3_cell", 2)
    ... )
    ```
    """
    assert_valid_resolution(resolution)
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_center_child",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def cell_to_children_size(cell: IntoExprColumn, resolution: HexResolution) -> pl.Expr:
    """
    Get the number of children cells at a specified resolution.

    #### Parameters
    - `cell`: IntoExprColumn
        H3 cells as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`.
    - `resolution`: int (0-15)

    #### Returns
    Expr
        Number of children cells.

    #### Examples
    ```python
    >>> df = pl.DataFrame({"h3_cell": [582692784209657855]})
    >>> df.with_columns(
    ...     num_children=polars_h3.cell_to_children_size("h3_cell", 2)
    ... )
    ```
    """
    assert_valid_resolution(resolution)
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_children_size",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def cell_to_children(cell: IntoExprColumn, resolution: HexResolution) -> pl.Expr:
    """
    Retrieve all children cells of an H3 cell at a specified resolution.

    #### Parameters
    - `cell`: IntoExprColumn
        H3 cells as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`.
    - `resolution`: int (0-15)

    #### Returns
    Expr
        List of child cells at the given resolution.

    #### Examples
    ```python
    >>> df = pl.DataFrame({"h3_cell": [582692784209657855]})
    >>> df.with_columns(
    ...     children=polars_h3.cell_to_children("h3_cell", 2)
    ... )
    ```
    """
    assert_valid_resolution(resolution)
    return register_plugin_function(
        args=[cell],
        plugin_path=LIB,
        function_name="cell_to_children",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def cell_to_child_pos(cell: IntoExprColumn, resolution: HexResolution) -> pl.Expr:
    """
    Get the position index of a child cell within its parent cell hierarchy.

    #### Parameters
    - `cell`: IntoExprColumn
        H3 cells as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`.
    - `resolution`: int (0-15)

    #### Returns
    Expr
        The child cell's position index.

    #### Examples
    ```python
    >>> df = pl.DataFrame({"h3_cell": [599686042433355776]})
    >>> df.with_columns(
    ...     child_pos=polars_h3.cell_to_child_pos("h3_cell", 2)
    ... )
    ```
    """

    assert_valid_resolution(resolution)
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
    Obtain the child cell at a given position index for a specified parent cell and resolution.

    #### Parameters
    - `parent`: IntoExprColumn
        H3 cells as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`.
    - `pos`: IntoExprColumn
        Position index as `pl.UInt64` or `pl.Int64`.
    - `resolution`: int (0-15)

    #### Returns
    Expr
        The child cell at the given position.

    #### Examples
    ```python
    >>> df = pl.DataFrame({
    ...     "parent": [582692784209657855],
    ...     "pos": [0]
    ... })
    >>> df.with_columns(
    ...     child=polars_h3.child_pos_to_cell("parent", "pos", 2)
    ... )
    ```
    """
    assert_valid_resolution(resolution)
    return register_plugin_function(
        args=[parent, pos],
        plugin_path=LIB,
        function_name="child_pos_to_cell",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def compact_cells(cells: IntoExprColumn) -> pl.Expr:
    """
    Compact a set of H3 cells into a minimal covering set. See [H3 documentation](https://h3geo.org/docs/highlights/indexing) for more details.

    #### Parameters
    - `cells`: IntoExprColumn
        H3 cells as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`.

    #### Returns
    Expr
        A compacted list of H3 cells.

    #### Examples
    ```python
    >>> df = pl.DataFrame({
    ...     "h3_cells": [[599686042433355775, 599686042433355776]]
    ... })
    >>> df.with_columns(
    ...     compact=polars_h3.compact_cells("h3_cells")
    ... )
    ```
    """
    return register_plugin_function(
        args=[cells],
        plugin_path=LIB,
        function_name="compact_cells",
        is_elementwise=True,
    )


def uncompact_cells(cells: IntoExprColumn, resolution: HexResolution) -> pl.Expr:
    """
    Uncompact a set of H3 cells to the specified resolution.

    #### Parameters
    - `cells`: IntoExprColumn
        H3 cells as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`.
    - `resolution`: int (0-15)

    #### Returns
    Expr
        A list of H3 cells at the specified resolution.

    #### Examples
    ```python
    >>> df = pl.DataFrame({
    ...     "compact_cells": [[582692784209657855]]
    ... })
    >>> df.with_columns(
    ...     full_set=polars_h3.uncompact_cells("compact_cells", 2)
    ... )
    ```
    """
    assert_valid_resolution(resolution)
    return register_plugin_function(
        args=[cells],
        plugin_path=LIB,
        function_name="uncompact_cells",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )
