# Vertex functions

Vertex mode allows encoding the topological vertexes of H3 cells.

---

## `cell_to_vertex`

Retrieve the H3 vertex index for a specific vertex of a given cell.

```python
plh3.cell_to_vertex(
    cell: IntoExprColumn,
    vertex_num: int
) -> pl.Expr
```

**Parameters**

- **cell** : IntoExprColumn  
  H3 cell index (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
- **vertex_num** : int  
  0-based vertex number. For hexagonal cells, valid range is `[0..5]`; for pentagonal cells, `[0..4]`.

**Returns**

- **Expr**  
  A Polars expression returning the corresponding H3 vertex index (`pl.UInt64` or `pl.Int64`), or `null` if invalid.

**Examples**

```python
>>> df = pl.DataFrame({"h3_cell": [599686042433355775]})
>>> df.with_columns(vertex=plh3.cell_to_vertex("h3_cell", 0))
shape: (1, 2)
┌─────────────────────┬─────────────────────┐
│ h3_cell             │ vertex              │
│ ---                 │ ---                 │
│ u64                 │ u64                 │
╞═════════════════════╪═════════════════════╡
│ 599686042433355775  │ 2473183459502194687 │
└─────────────────────┴─────────────────────┘
```

**Errors**

- `ComputeError`: If `vertex_num` is out of range or the cell is invalid.

---

## `cell_to_vertexes`

Retrieve all vertex indices for a given H3 cell.

```python
plh3.cell_to_vertexes(
    cell: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **cell** : IntoExprColumn  
  H3 cell index (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

**Returns**

- **Expr**  
  A Polars expression returning a list of H3 vertex indices (6 for a hex cell, 5 for a pentagon).

**Examples**

```python
>>> df = pl.DataFrame({"h3_cell": [599686042433355775]})
>>> df.with_columns(vertexes=plh3.cell_to_vertexes("h3_cell"))
shape: (1, 2)
┌─────────────────────┬────────────────────────────────────────────────┐
│ h3_cell             │ vertexes                                       │
│ ---                 │ ---                                             │
│ u64                 │ list[u64]                                       │
╞═════════════════════╪════════════════════════════════════════════════╡
│ 599686042433355775  │ [2473183459502194687, 2545241069646249983, … ] │
└─────────────────────┴────────────────────────────────────────────────┘
```

---

## `vertex_to_latlng`

Convert an H3 vertex index into its latitude and longitude coordinates.

```python
plh3.vertex_to_latlng(
    vertex: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **vertex** : IntoExprColumn  
  H3 vertex index (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

**Returns**

- **Expr**  
  A Polars expression returning a two-element list `[latitude, longitude]` (`Float64`, `Float64`) or `null` if invalid.

**Examples**

```python
>>> df = pl.DataFrame({"vertex": [2459626752788398079]})
>>> df.with_columns(coords=plh3.vertex_to_latlng("vertex"))
shape: (1, 2)
┌──────────────────────┬─────────────────────────┐
│ vertex               │ coords                  │
│ ---                  │ ---                     │
│ u64                  │ list[f64]               │
╞══════════════════════╪═════════════════════════╡
│ 2459626752788398079  │ [39.38084284181812, 88.57496213785487] │
└──────────────────────┴─────────────────────────┘
```

---

## `is_valid_vertex`

Check whether an H3 index represents a valid H3 vertex.

```python
plh3.is_valid_vertex(
    vertex: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **vertex** : IntoExprColumn  
  H3 vertex index.

**Returns**

- **Expr**  
  A boolean Polars expression: `true` if valid, `false` otherwise.

**Examples**

```python
>>> df = pl.DataFrame({"vertex": [2459626752788398079]})
>>> df.with_columns(valid=plh3.is_valid_vertex("vertex"))
shape: (1, 2)
┌──────────────────────┬──────────┐
│ vertex               │ valid    │
│ ---                  │ ---      │
│ u64                  │ bool     │
╞══════════════════════╪══════════╡
│ 2459626752788398079  │ true     │
└──────────────────────┴──────────┘
```
