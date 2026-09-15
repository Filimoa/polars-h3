# Grid traversal

Find nearby cells, grid distances, and paths.

## `grid_disk`

```python
plh3.grid_disk(
    cell: IntoExprColumn,
    k: int | IntoExprColumn,
) -> pl.Expr
```

Return the origin and all cells no more than `k` grid steps away.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"cell": ["85283473fffffff"]})
df.select(cells=plh3.grid_disk("cell", k=1))
```

```text
shape: (1, 1)
┌───────────────────────────┐
│ cells                     │
│ ---                       │
│ list[str]                 │
╞═══════════════════════════╡
│ ["85283473fffffff", "852… │
└───────────────────────────┘
```

## `grid_ring`

```python
plh3.grid_ring(
    cell: IntoExprColumn,
    k: int | IntoExprColumn,
) -> pl.Expr
```

Return cells exactly `k` grid steps from the origin.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"cell": ["85283473fffffff"]})
df.select(cells=plh3.grid_ring("cell", k=1))
```

```text
shape: (1, 1)
┌───────────────────────────┐
│ cells                     │
│ ---                       │
│ list[str]                 │
╞═══════════════════════════╡
│ ["8528340bfffffff", "852… │
└───────────────────────────┘
```

## `grid_distance`

```python
plh3.grid_distance(
    origin: IntoExprColumn,
    destination: IntoExprColumn,
) -> pl.Expr
```

Return the minimum number of grid steps between two cells.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {
        "origin": ["85283473fffffff"],
        "destination": ["85283447fffffff"],
    }
)
df.select(distance=plh3.grid_distance("origin", "destination"))
```

```text
shape: (1, 1)
┌──────────┐
│ distance │
│ ---      │
│ i32      │
╞══════════╡
│ 1        │
└──────────┘
```

## `grid_path_cells`

```python
plh3.grid_path_cells(
    origin: IntoExprColumn,
    destination: IntoExprColumn,
) -> pl.Expr
```

Return a minimal contiguous path including both endpoints.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {
        "origin": ["85283473fffffff"],
        "destination": ["8528341bfffffff"],
    }
)
df.select(path=plh3.grid_path_cells("origin", "destination"))
```

```text
shape: (1, 1)
┌───────────────────────────┐
│ path                      │
│ ---                       │
│ list[str]                 │
╞═══════════════════════════╡
│ ["85283473fffffff", "852… │
└───────────────────────────┘
```

!!! note "Traversal failures"

    Origins and destinations must have compatible resolutions. Pentagon
    distortion can make some paths unavailable.
