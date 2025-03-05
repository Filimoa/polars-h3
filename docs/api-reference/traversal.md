# Grid traversal functions

Grid traversal allows finding cells in the vicinity of an origin cell, and determining how to traverse the grid from one cell to another.

---

## `grid_distance`

Compute the grid distance between two H3 cells.

```python
plh3.grid_distance(
    origin: IntoExprColumn,
    destination: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **origin** : IntoExprColumn  
  H3 cell index (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
- **destination** : IntoExprColumn  
  H3 cell index (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

**Returns**

- **Expr**  
  A Polars expression returning the minimum number of steps between `origin` and `destination`, or `null` if it cannot be computed.

**Examples**

```python
>>> df = pl.DataFrame({
...     "start": [605035864166236159],
...     "end": [605034941150920703],
... })
>>> df.select(plh3.grid_distance("start", "end"))
shape: (1, 1)
┌───────────────┐
│ grid_distance │
│ ---           │
│ i64           │
╞═══════════════╡
│ 5             │
└───────────────┘
```

**Errors**

- `ComputeError`: If inputs are invalid (e.g. different resolutions or pentagon issues).
- Returns `None`: If no valid distance can be computed.

---

## `grid_ring`

Produce a "hollow ring" of cells at exactly grid distance `k` from the origin cell.

```python
plh3.grid_ring(
    cell: IntoExprColumn,
    k: int | IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **cell** : IntoExprColumn  
  H3 cell index (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
- **k** : int | IntoExprColumn  
  The ring distance. Must be non-negative.

**Returns**

- **Expr**  
  A Polars expression returning a list of H3 cells at distance `k`. May contain `null` items if pentagonal distortion is encountered.

**Examples**

```python
>>> df = pl.DataFrame({"input": [622054503267303423]})
>>> df.select(plh3.grid_ring("input", 1))
shape: (1, 1)
┌───────────────────────────────────┐
│ grid_ring                         │
│ ---                               │
│ list[u64]                         │
╞═══════════════════════════════════╡
│ [622054502770606079, 622054502770…]│
└───────────────────────────────────┘
```

```python
>>> df = pl.DataFrame({"input": [622054503267303423], "k": [1]})
>>> df.select(plh3.grid_ring("input", "k"))
shape: (1, 1)
┌───────────────────────────────────┐
│ grid_ring                         │
│ ---                               │
│ list[u64]                         │
╞═══════════════════════════════════╡
│ [622054502770606079, 622054502770…]│
└───────────────────────────────────┘
```

**Returns**

- `ValueError`: If `k < 0`.
- `ComputeError`: If pentagonal distortion or invalid inputs prevent computation.

---

## `grid_disk`

Produce a “filled-in disk” of cells within grid distance `k` of the origin cell.

```python
plh3.grid_disk(
    cell: IntoExprColumn,
    k: int | IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **cell** : IntoExprColumn  
  H3 cell index (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
- **k** : int | IntoExprColumn  
  The maximum distance from the origin. Must be non-negative.

**Returns**

- **Expr**  
  A Polars expression returning a list of H3 cells from distance 0 up to `k`.  
  May contain `null` items if pentagonal distortion is encountered.

**Examples**

```python
>>> df = pl.DataFrame({"input": [622054503267303423]})
>>> df.select(plh3.grid_disk("input", 1))
shape: (1, 1)
┌───────────────────────────────────┐
│ grid_disk                         │
│ ---                               │
│ list[u64]                         │
╞═══════════════════════════════════╡
│ [622054503267303423, 622054502770…]│
└───────────────────────────────────┘
```

```python
>>> df = pl.DataFrame({"input": [622054503267303423], "k": [1]})
>>> df.select(plh3.grid_disk("input", "k"))
shape: (1, 1)
┌───────────────────────────────────┐
│ grid_disk                         │
│ ---                               │
│ list[u64]                         │
╞═══════════════════════════════════╡
│ [622054503267303423, 622054502770…]│
└───────────────────────────────────┘
```

**Returns**

- `ValueError`: If `k < 0`.
- `ComputeError`: If pentagonal distortion or invalid inputs prevent computation.

---

## `grid_path_cells`

Find a minimal contiguous path of cells from `origin` to `destination`.

```python
plh3.grid_path_cells(
    origin: IntoExprColumn,
    destination: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **origin** : IntoExprColumn  
  H3 cell index for the starting cell.
- **destination** : IntoExprColumn  
  H3 cell index for the ending cell.

**Returns**

- **Expr**  
  A Polars expression returning a list of H3 cells forming a minimal path from `origin` to `destination`, or `null` if no valid path is found.

**Examples**

```python
>>> df = pl.DataFrame({
...     "start": [605035864166236159],
...     "end": [605034941150920703],
... })
>>> df.select(plh3.grid_path_cells("start", "end"))
shape: (1, 1)
┌───────────────────────────────────┐
│ grid_path_cells                   │
│ ---                               │
│ list[u64]                         │
╞═══════════════════════════════════╡
│ [605035864166236159, 605035861750…]│
└───────────────────────────────────┘
```

**Returns**

- `ComputeError`: If no valid path can be computed (e.g., due to invalid inputs or pentagon issues).
