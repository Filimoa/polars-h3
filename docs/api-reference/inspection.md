# Inspection functions

These functions provide metadata about an H3 index, such as its resolution or base cell, and provide utilities for converting into and out of the 64-bit representation of an H3 index.

---

## `get_resolution`

Retrieve the resolution of H3 indices (cells, edges, or vertices).

```python
plh3.get_resolution(
    expr: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **expr** : IntoExprColumn  
  Column/expression containing H3 indices (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

**Returns**

- **Expr**  
  A Polars expression yielding an integer resolution (`0–15`) for each H3 index.

**Examples**

```python
>>> df = pl.DataFrame({
...     "h3_cell": [599686042433355775]
... })
>>> df.with_columns(
...     resolution=plh3.get_resolution("h3_cell")
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

---

## `str_to_int`

Convert string H3 indices into their unsigned 64-bit integer representation.

```python
plh3.str_to_int(
    expr: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **expr** : IntoExprColumn  
  String-based H3 cells (e.g., `"85283473fffffff"`).

**Returns**

- **Expr**  
  A Polars expression yielding `pl.UInt64` indices, or `null` for invalid strings.

**Examples**

```python
>>> df = pl.DataFrame({
...     "h3_str": ["85283473fffffff", "invalid_index"]
... })
>>> df.with_columns(
...     h3_int=plh3.str_to_int("h3_str")
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

---

## `int_to_str`

Convert integer H3 indices into their string representation.

```python
plh3.int_to_str(
    expr: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **expr** : IntoExprColumn  
  Integer-based H3 cells (`pl.UInt64`, `pl.Int64`).

**Returns**

- **Expr**  
  A Polars expression yielding string representations of H3 indices, or `null` for invalid inputs.

**Examples**

```python
>>> df = pl.DataFrame({
...     "h3_int": [599686042433355775, -1]
... })
>>> df.with_columns(
...     h3_str=plh3.int_to_str("h3_int")
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

---

## `is_valid_cell`

Check if H3 cell indices are valid.

```python
plh3.is_valid_cell(
    expr: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **expr** : IntoExprColumn  
  H3 cells (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

**Returns**

- **Expr**  
  A boolean Polars expression: `true` if valid, `false` otherwise.

**Examples**

```python
>>> df = pl.DataFrame({
...     "h3_cell": ["85283473fffffff", "invalid_cell"]
... })
>>> df.with_columns(
...     valid=plh3.is_valid_cell("h3_cell")
... )
shape: (2, 2)
┌─────────────────────┬───────┐
│ h3_cell             │ valid │
│ ---                 │ ---   │
│ str                 │ bool  │
╞═════════════════════╪═══════╡
│ 85283473fffffff     │ true  │
│ invalid_cell        │ false │
└─────────────────────┴───────┘
```

---

## `is_pentagon`

Determine if H3 cells are pentagons.

```python
plh3.is_pentagon(
    expr: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **expr** : IntoExprColumn  
  H3 cells (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

**Returns**

- **Expr**  
  A boolean Polars expression indicating if each H3 cell is a pentagon.

**Examples**

```python
>>> df = pl.DataFrame({
...     "h3_cell": [585961082523222015, 599686042433355775]
... })
>>> df.with_columns(
...     is_pent=plh3.is_pentagon("h3_cell")
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

---

## `is_res_class_III`

Check if H3 cells belong to the Class III resolution set.

```python
plh3.is_res_class_III(
    expr: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **expr** : IntoExprColumn  
  H3 cells (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

**Returns**

- **Expr**  
  A boolean Polars expression indicating if each cell is Class III.

**Examples**

```python
>>> df = pl.DataFrame({
...     "h3_cell": [582692784209657855, 586265647244115967]
... })
>>> df.with_columns(
...     is_class_3=plh3.is_res_class_III("h3_cell")
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

---

## `get_icosahedron_faces`

Retrieve the icosahedron faces intersected by an H3 cell.

```python
plh3.get_icosahedron_faces(
    expr: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **expr** : IntoExprColumn  
  H3 cells (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

**Returns**

- **Expr**  
  A Polars expression returning a list of intersected face indices.

**Examples**

```python
>>> df = pl.DataFrame({
...     "h3_cell": [599686042433355775]
... })
>>> df.with_columns(
...     faces=plh3.get_icosahedron_faces("h3_cell")
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

---

## `cell_to_parent`

Retrieve the parent cell of a given H3 cell at a specified resolution.

```python
plh3.cell_to_parent(
    cell: IntoExprColumn,
    resolution: HexResolution
) -> pl.Expr
```

**Parameters**

- **cell** : IntoExprColumn  
  H3 cells (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
- **resolution** : int in `[0, 15]`  
  Target parent resolution.

**Returns**

- **Expr**  
  A Polars expression returning the parent cell.

**Examples**

```python
>>> df = pl.DataFrame({"h3_cell": [599686042433355775]})
>>> df.with_columns(
...     parent=plh3.cell_to_parent("h3_cell", 1)
... )
shape: (1, 2)
┌─────────────────────┬─────────────────────┐
│ h3_cell             │ parent              │
│ ---                 │ ---                 │
│ u64                 │ u64                 │
╞═════════════════════╪═════════════════════╡
│ 599686042433355775  │ 593686042413355775  │
└─────────────────────┴─────────────────────┘
```

---

## `cell_to_center_child`

Retrieve the center child cell of an H3 cell at a specified resolution.

```python
plh3.cell_to_center_child(
    cell: IntoExprColumn,
    resolution: HexResolution
) -> pl.Expr
```

**Parameters**

- **cell** : IntoExprColumn  
  H3 cells (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
- **resolution** : int in `[0, 15]`

**Returns**

- **Expr**  
  A Polars expression returning the center child cell at the given resolution.

**Examples**

```python
>>> df = pl.DataFrame({"h3_cell": [582692784209657855]})
>>> df.with_columns(
...     center_child=plh3.cell_to_center_child("h3_cell", 2)
... )
shape: (1, 2)
┌─────────────────────┬─────────────────┐
│ h3_cell             │ center_child    │
│ ---                 │ ---             │
│ u64                 │ u64             │
╞═════════════════════╪═════════════════╡
│ 582692784209657855  │ ...             │
└─────────────────────┴─────────────────┘
```

---

## `cell_to_children_size`

Get the number of children cells at a specified resolution.

```python
plh3.cell_to_children_size(
    cell: IntoExprColumn,
    resolution: HexResolution
) -> pl.Expr
```

**Parameters**

- **cell** : IntoExprColumn  
  H3 cells (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
- **resolution** : int in `[0, 15]`

**Returns**

- **Expr**  
  A Polars expression returning the number of children cells.

**Examples**

```python
>>> df = pl.DataFrame({"h3_cell": [582692784209657855]})
>>> df.with_columns(
...     num_children=plh3.cell_to_children_size("h3_cell", 2)
... )
shape: (1, 2)
┌─────────────────────┬──────────────┐
│ h3_cell             │ num_children │
│ ---                 │ ---          │
│ u64                 │ u64          │
╞═════════════════════╪══════════════╡
│ 582692784209657855  │ 7            │
└─────────────────────┴──────────────┘
```

---

## `cell_to_children`

Retrieve all children cells of an H3 cell at a specified resolution.

```python
plh3.cell_to_children(
    cell: IntoExprColumn,
    resolution: HexResolution
) -> pl.Expr
```

**Parameters**

- **cell** : IntoExprColumn  
  H3 cells (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
- **resolution** : int in `[0, 15]`

**Returns**

- **Expr**  
  A Polars expression returning a list of child cells at the given resolution.

**Examples**

```python
>>> df = pl.DataFrame({"h3_cell": [582692784209657855]})
>>> df.with_columns(
...     children=plh3.cell_to_children("h3_cell", 2)
... )
shape: (1, 2)
┌─────────────────────┬───────────────────────────────────┐
│ h3_cell             │ children                          │
│ ---                 │ ---                               │
│ u64                 │ list[u64]                         │
╞═════════════════════╪═══════════════════════════════════╡
│ 582692784209657855  │ [587192535546331135, ...]         │
└─────────────────────┴───────────────────────────────────┘
```

---

## `cell_to_child_pos`

Get the position index of a child cell within its parent cell hierarchy.

```python
plh3.cell_to_child_pos(
    cell: IntoExprColumn,
    resolution: HexResolution
) -> pl.Expr
```

**Parameters**

- **cell** : IntoExprColumn  
  H3 cells (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
- **resolution** : int in `[0, 15]`

**Returns**

- **Expr**  
  A Polars expression returning the child cell’s position index.

**Examples**

```python
>>> df = pl.DataFrame({"h3_cell": [582692784209657855]})
>>> df.with_columns(
...     child_pos=plh3.cell_to_child_pos("h3_cell", 2)
... )
shape: (1, 2)
┌─────────────────────┬───────────┐
│ h3_cell             │ child_pos │
│ ---                 │ ---       │
│ u64                 │ u64       │
╞═════════════════════╪═══════════╡
│ 582692784209657855  │ 0       │
└─────────────────────┴───────────┘
```

---

## `child_pos_to_cell`

Obtain the child cell at a given position index for a specified parent cell and resolution.

```python
plh3.child_pos_to_cell(
    parent: IntoExprColumn,
    pos: IntoExprColumn,
    resolution: HexResolution
) -> pl.Expr
```

**Parameters**

- **parent** : IntoExprColumn  
  H3 cell index (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
- **pos** : IntoExprColumn  
  Position index (`pl.UInt64` or `pl.Int64`).
- **resolution** : int in `[0, 15]`

**Returns**

- **Expr**  
  A Polars expression returning the child cell at the given position.

**Examples**

```python
>>> df = pl.DataFrame({
...     "parent": [582692784209657855],
...     "pos": [0]
... })
>>> df.with_columns(
...     child=plh3.child_pos_to_cell("parent", "pos", 2)
... )
shape: (1, 2)
┌─────────────────────┬──────────┐
│ parent              │ child    │
│ ---                 │ ---      │
│ u64                 │ u64      │
╞═════════════════════╪══════════╡
│ 582692784209657855  │ ...      │
└─────────────────────┴──────────┘
```

---

## `compact_cells`

Compact a set of H3 cells into a minimal covering set.

```python
plh3.compact_cells(
    cells: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **cells** : IntoExprColumn  
  H3 cells (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`), possibly in a list.

**Returns**

- **Expr**  
  A Polars expression returning a compacted list of H3 cells.

**Examples**

```python
>>> df = pl.DataFrame({
...     "h3_cells": [[599686042433355775, 599686042433355776]]
... })
>>> df.with_columns(
...     compact=plh3.compact_cells("h3_cells")
... )
shape: (1, 2)
┌───────────────────────────────────┬────────────────────────────────┐
│ h3_cells                          │ compact                        │
│ ---                               │ ---                            │
│ list[u64]                         │ list[u64]                      │
╞═══════════════════════════════════╪════════════════════════════════╡
│ [599686042433355775, 5996860424…] │ [599686042433355775]           │
└───────────────────────────────────┴────────────────────────────────┘
```

---

## `uncompact_cells`

Uncompact a set of H3 cells to the specified resolution.

```python
plh3.uncompact_cells(
    cells: IntoExprColumn,
    resolution: HexResolution
) -> pl.Expr
```

**Parameters**

- **cells** : IntoExprColumn  
  H3 cells (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
- **resolution** : int in `[0, 15]`

**Returns**

- **Expr**  
  A Polars expression returning a list of H3 cells at the specified resolution.

**Examples**

```python
>>> df = pl.DataFrame({
...     "compact_cells": [[582692784209657855]]
... })
>>> df.with_columns(
...     full_set=plh3.uncompact_cells("compact_cells", 2)
... )
shape: (1, 2)
┌──────────────────────┬────────────────────────────────┐
│ compact_cells        │ full_set                       │
│ ---                  │ ---                            │
│ list[u64]            │ list[u64]                      │
╞══════════════════════╪════════════════════════════════╡
│ [582692784209657855] │ [587192535546331135, ...]      │
└──────────────────────┴────────────────────────────────┘
```

---

**Notes**

- A `ComputeError` may occur if inputs are invalid or the operation cannot be completed.
- A `ValueError` is raised if the `resolution` is outside `[0, 15]`.
