# Vertices

Inspect the vertices shared by H3 cells.

## `cell_to_vertex`

```python
plh3.cell_to_vertex(cell: IntoExprColumn, vertex_num: int) -> pl.Expr
```

Return one vertex of each cell by its zero-based vertex number.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {"cell": [599686042433355775]},
    schema_overrides={"cell": pl.UInt64},
)
df.select(vertex=plh3.cell_to_vertex("cell", 0))
```

```text
shape: (1, 1)
┌─────────────────────┐
│ vertex              │
│ ---                 │
│ u64                 │
╞═════════════════════╡
│ 2473183459502194687 │
└─────────────────────┘
```

## `cell_to_vertexes`

```python
plh3.cell_to_vertexes(cell: IntoExprColumn) -> pl.Expr
```

Return all vertices of each cell as a list.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {"cell": [599686042433355775]},
    schema_overrides={"cell": pl.UInt64},
)
df.select(vertices=plh3.cell_to_vertexes("cell"))
```

```text
shape: (1, 1)
┌───────────────────────────┐
│ vertices                  │
│ ---                       │
│ list[u64]                 │
╞═══════════════════════════╡
│ [2473183459502194687, 25… │
└───────────────────────────┘
```

## `vertex_to_latlng`

```python
plh3.vertex_to_latlng(vertex: IntoExprColumn) -> pl.Expr
```

Return each vertex's latitude and longitude in degrees.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {"vertex": [2459626752788398079]},
    schema_overrides={"vertex": pl.UInt64},
)
df.select(coordinates=plh3.vertex_to_latlng("vertex"))
```

```text
shape: (1, 1)
┌────────────────────────┐
│ coordinates            │
│ ---                    │
│ list[f64]              │
╞════════════════════════╡
│ [39.380843, 88.574962] │
└────────────────────────┘
```

## `is_valid_vertex`

```python
plh3.is_valid_vertex(vertex: IntoExprColumn) -> pl.Expr
```

Return whether each value is a valid H3 vertex.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {"index": [2459626752788398079, 599686042433355775]},
    schema_overrides={"index": pl.UInt64},
)
df.select(valid=plh3.is_valid_vertex("index"))
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

!!! note "Vertex numbering"

    `cell_to_vertexes` retains the package's public spelling for compatibility.
    An invalid `vertex_num` can raise `polars.exceptions.ComputeError`.
