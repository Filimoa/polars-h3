# Directed edges

Work with directed edges between neighboring H3 cells.

## `are_neighbor_cells`

```python
plh3.are_neighbor_cells(
    origin: IntoExprColumn,
    destination: IntoExprColumn,
) -> pl.Expr
```

Return whether two cells are neighbors.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {
        "origin": ["85283473fffffff"],
        "destination": ["85283447fffffff"],
    }
)
df.select(neighbors=plh3.are_neighbor_cells("origin", "destination"))
```

```text
shape: (1, 1)
┌───────────┐
│ neighbors │
│ ---       │
│ bool      │
╞═══════════╡
│ true      │
└───────────┘
```

## `cells_to_directed_edge`

```python
plh3.cells_to_directed_edge(
    origin: IntoExprColumn,
    destination: IntoExprColumn,
) -> pl.Expr
```

Create the directed edge from `origin` to `destination`.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {
        "origin": ["85283473fffffff"],
        "destination": ["85283447fffffff"],
    }
)
df.select(edge=plh3.cells_to_directed_edge("origin", "destination"))
```

```text
shape: (1, 1)
┌─────────────────────┐
│ edge                │
│ ---                 │
│ u64                 │
╞═════════════════════╡
│ 1608492358964346879 │
└─────────────────────┘
```

## `is_valid_directed_edge`

```python
plh3.is_valid_directed_edge(edge: IntoExprColumn) -> pl.Expr
```

Return whether each value is a valid directed edge.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {"index": [1608492358964346879, 599686042433355775]},
    schema_overrides={"index": pl.UInt64},
)
df.select(valid=plh3.is_valid_directed_edge("index"))
```

```text
shape: (2, 1)
┌───────┐
│ valid │
│ ---   │
│ bool  │
╞═══════╡
│ true  │
│ false │
└───────┘
```

## `get_directed_edge_origin`

```python
plh3.get_directed_edge_origin(edge: IntoExprColumn) -> pl.Expr
```

Return the origin cell of each directed edge.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {"edge": [1608492358964346879]},
    schema_overrides={"edge": pl.UInt64},
)
df.select(origin=plh3.get_directed_edge_origin("edge"))
```

```text
shape: (1, 1)
┌────────────────────┐
│ origin             │
│ ---                │
│ u64                │
╞════════════════════╡
│ 599686042433355775 │
└────────────────────┘
```

## `get_directed_edge_destination`

```python
plh3.get_directed_edge_destination(edge: IntoExprColumn) -> pl.Expr
```

Return the destination cell of each directed edge.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {"edge": [1608492358964346879]},
    schema_overrides={"edge": pl.UInt64},
)
df.select(destination=plh3.get_directed_edge_destination("edge"))
```

```text
shape: (1, 1)
┌────────────────────┐
│ destination        │
│ ---                │
│ u64                │
╞════════════════════╡
│ 599686030622195711 │
└────────────────────┘
```

## `directed_edge_to_cells`

```python
plh3.directed_edge_to_cells(edge: IntoExprColumn) -> pl.Expr
```

Return the origin and destination cells of each directed edge.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {"edge": [1608492358964346879]},
    schema_overrides={"edge": pl.UInt64},
)
df.select(cells=plh3.directed_edge_to_cells("edge"))
```

```text
shape: (1, 1)
┌───────────────────────────┐
│ cells                     │
│ ---                       │
│ list[u64]                 │
╞═══════════════════════════╡
│ [599686042433355775, 599… │
└───────────────────────────┘
```

## `origin_to_directed_edges`

```python
plh3.origin_to_directed_edges(cell: IntoExprColumn) -> pl.Expr
```

Return all directed edges originating from each cell.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {"cell": [599686042433355775]},
    schema_overrides={"cell": pl.UInt64},
)
df.select(edges=plh3.origin_to_directed_edges("cell"))
```

```text
shape: (1, 1)
┌───────────────────────────┐
│ edges                     │
│ ---                       │
│ list[u64]                 │
╞═══════════════════════════╡
│ [1248204388774707199, 13… │
└───────────────────────────┘
```

## `directed_edge_to_boundary`

```python
plh3.directed_edge_to_boundary(edge: IntoExprColumn) -> pl.Expr
```

Return each directed edge's boundary coordinates.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {"edge": [1608492358964346879]},
    schema_overrides={"edge": pl.UInt64},
)
df.select(boundary=plh3.directed_edge_to_boundary("edge"))
```

```text
shape: (1, 1)
┌───────────────────────────┐
│ boundary                  │
│ ---                       │
│ list[f64]                 │
╞═══════════════════════════╡
│ [37.271356, -121.91508, … │
└───────────────────────────┘
```

!!! note "Edge construction"

    The origin and destination must be neighboring cells at the same resolution.
    Invalid inputs can raise `polars.exceptions.ComputeError`.
