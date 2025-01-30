# Directed edge functions

Directed edges allow encoding the directed (that is, which cell is the origin and which is the destination can be determined) edge from one cell to a neighboring cell.

---

## `are_neighbor_cells`

Determine whether two H3 cells are neighbors.

```python
plh3.are_neighbor_cells(
    origin: IntoExprColumn,
    destination: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **origin** : IntoExprColumn  
  H3 cell index serving as the origin (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
- **destination** : IntoExprColumn  
  H3 cell index serving as the destination (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

**Returns**

- **Expr**  
  A boolean Polars expression: `true` if the cells share an edge, `false` otherwise.

**Examples**

```python
>>> df = pl.DataFrame({
...     "cell1": [599686042433355775],
...     "cell2": [599686030622195711],
... })
>>> df.with_columns(neighbors=plh3.are_neighbor_cells("cell1", "cell2"))
shape: (1, 3)
┌─────────────────────┬─────────────────────┬───────────┐
│ cell1               │ cell2               │ neighbors │
│ ---                 │ ---                 │ ---       │
│ u64                 │ u64                 │ bool      │
╞═════════════════════╪═════════════════════╪═══════════╡
│ 599686042433355775  │ 599686030622195711  │ true      │
└─────────────────────┴─────────────────────┴───────────┘
```

**Errors**

- `ComputeError`: If invalid or null indices are provided.

---

## `cells_to_directed_edge`

Create a directed H3 edge from two neighboring cells.

```python
plh3.cells_to_directed_edge(
    origin: IntoExprColumn,
    destination: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **origin** : IntoExprColumn  
  Origin H3 cell index.
- **destination** : IntoExprColumn  
  Destination H3 cell index.

**Returns**

- **Expr**  
  A Polars expression returning the H3 directed edge index.

**Examples**

```python
>>> df = pl.DataFrame({
...     "origin": [599686042433355775],
...     "destination": [599686030622195711],
... })
>>> df.with_columns(edge=plh3.cells_to_directed_edge("origin", "destination"))
shape: (1, 3)
┌─────────────────────┬─────────────────────┬─────────────────────┐
│ origin              │ destination         │ edge                │
│ ---                 │ ---                 │ ---                 │
│ u64                 │ u64                 │ u64                 │
╞═════════════════════╪═════════════════════╪═════════════════════╡
│ 599686042433355775  │ 599686030622195711  │ 1608492358964346879 │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

**Errors**

- `ComputeError`: If the cells are not neighbors or invalid.

---

## `is_valid_directed_edge`

Check if an H3 index is a valid directed edge.

```python
plh3.is_valid_directed_edge(
    edge: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **edge** : IntoExprColumn  
  H3 index to validate.

**Returns**

- **Expr**  
  A boolean Polars expression: `true` if `edge` is a valid directed edge, `false` otherwise.

**Examples**

```python
>>> df = pl.DataFrame({"edge": ["115283473fffffff"]})
>>> df.with_columns(valid=plh3.is_valid_directed_edge("edge"))
shape: (1, 2)
┌───────────────────────┬──────────┐
│ edge                  │ valid    │
│ ---                   │ ---      │
│ str                   │ bool     │
╞═══════════════════════╪══════════╡
│ 115283473fffffff      │ true     │
└───────────────────────┴──────────┘
```

**Errors**

- `ComputeError`: If the input is invalid or null.

---

## `get_directed_edge_origin`

Extract the origin cell from a directed H3 edge.

```python
plh3.get_directed_edge_origin(
    edge: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **edge** : IntoExprColumn  
  H3 directed edge index.

**Returns**

- **Expr**  
  A Polars expression returning the origin cell (`pl.UInt64` or `pl.Utf8`).

**Examples**

```python
>>> df = pl.DataFrame({"edge": [1608492358964346879]})
>>> df.with_columns(origin=plh3.get_directed_edge_origin("edge"))
shape: (1, 2)
┌─────────────────────┬─────────────────────┐
│ edge                │ origin              │
│ ---                 │ ---                 │
│ u64                 │ u64                 │
╞═════════════════════╪═════════════════════╡
│ 1608492358964346879 │ 599686042433355775  │
└─────────────────────┴─────────────────────┘
```

**Errors**

- `ComputeError`: If `edge` is invalid or null.

---

## `get_directed_edge_destination`

Extract the destination cell from a directed H3 edge.

```python
plh3.get_directed_edge_destination(
    edge: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **edge** : IntoExprColumn  
  H3 directed edge index.

**Returns**

- **Expr**  
  A Polars expression returning the destination cell (`pl.UInt64` or `pl.Utf8`).

**Examples**

```python
>>> df = pl.DataFrame({"edge": [1608492358964346879]})
>>> df.with_columns(destination=plh3.get_directed_edge_destination("edge"))
shape: (1, 2)
┌─────────────────────┬─────────────────────┐
│ edge                │ destination         │
│ ---                 │ ---                 │
│ u64                 │ u64                 │
╞═════════════════════╪═════════════════════╡
│ 1608492358964346879 │ 599686030622195711  │
└─────────────────────┴─────────────────────┘
```

**Errors**

- `ComputeError`: If `edge` is invalid or null.

---

## `directed_edge_to_cells`

Retrieve the origin-destination cell pair from a directed edge.

```python
plh3.directed_edge_to_cells(
    edge: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **edge** : IntoExprColumn  
  H3 directed edge index.

**Returns**

- **Expr**  
  A Polars expression returning `[origin, destination]` as `[pl.UInt64, pl.UInt64]` (or `[pl.Utf8, pl.Utf8]`).

**Examples**

```python
>>> df = pl.DataFrame({"edge": [1608492358964346879]})
>>> df.with_columns(cells=plh3.directed_edge_to_cells("edge"))
shape: (1, 2)
┌─────────────────────┬─────────────────────┐
│ edge                │ cells               │
│ ---                 │ ---                 │
│ u64                 │ list[u64]           │
╞═════════════════════╪═════════════════════╡
│ 1608492358964346879 │ [599686042433355775,… │
└─────────────────────┴─────────────────────┘
```

**Errors**

- `ComputeError`: If `edge` is invalid or null.

---

## `origin_to_directed_edges`

List all directed edges originating from a given cell.

```python
plh3.origin_to_directed_edges(
    cell: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **cell** : IntoExprColumn  
  H3 cell index serving as the origin.

**Returns**

- **Expr**  
  A Polars expression returning a list of directed edges (`pl.UInt64` or `pl.Utf8`).

**Examples**

```python
>>> df = pl.DataFrame({"h3_cell": [599686042433355775]})
>>> df.with_columns(edges=plh3.origin_to_directed_edges("h3_cell"))
shape: (1, 2)
┌─────────────────────┬─────────────────────────────────┐
│ h3_cell             │ edges                           │
│ ---                 │ ---                             │
│ u64                 │ list[u64]                       │
╞═════════════════════╪═════════════════════════════════╡
│ 599686042433355775  │ [1608492358964346879,…]          │
└─────────────────────┴─────────────────────────────────┘
```

**Errors**

- `ComputeError`: If `cell` is invalid or null.

---

## `directed_edge_to_boundary`

Retrieve the geographic boundary (list of lat/lng pairs) defining a directed edge.

```python
plh3.directed_edge_to_boundary(
    edge: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **edge** : IntoExprColumn  
  H3 directed edge index.

**Returns**

- **Expr**  
  A Polars expression returning a list of `[lat, lng]` pairs, each itself a two-element list.

**Examples**

```python
>>> df = pl.DataFrame({"edge": [1608492358964346879]})
>>> df.with_columns(boundary=plh3.directed_edge_to_boundary("edge"))
shape: (1, 2)
┌─────────────────────┬───────────────────────────────┐
│ edge                │ boundary                      │
│ ---                 │ ---                           │
│ u64                 │ list[list[f64]]               │
╞═════════════════════╪═══════════════════════════════╡
│ 1608492358964346879 │ [[37.3457, -121.9763], … ]    │
└─────────────────────┴───────────────────────────────┘
```

**Errors**

- `ComputeError`: If `edge` is invalid, null, or its boundary cannot be computed.
