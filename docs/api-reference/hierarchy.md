# Hierarchical grid functions

Move between H3 resolutions and compact or expand cell coverings.

## `cell_to_parent`

```python
plh3.cell_to_parent(cell: IntoExprColumn, resolution: int) -> pl.Expr
```

Return the ancestor at `resolution`.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"cell": ["85283473fffffff"]})
df.select(parent=plh3.cell_to_parent("cell", resolution=4))
```

```text
shape: (1, 1)
┌─────────────────┐
│ parent          │
│ ---             │
│ str             │
╞═════════════════╡
│ 8428347ffffffff │
└─────────────────┘
```

## `cell_to_center_child`

```python
plh3.cell_to_center_child(cell: IntoExprColumn, resolution: int) -> pl.Expr
```

Return the center descendant at `resolution`.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"cell": ["8428347ffffffff"]})
df.select(center_child=plh3.cell_to_center_child("cell", resolution=5))
```

```text
shape: (1, 1)
┌─────────────────┐
│ center_child    │
│ ---             │
│ str             │
╞═════════════════╡
│ 85283463fffffff │
└─────────────────┘
```

## `cell_to_children_size`

```python
plh3.cell_to_children_size(
    cell: IntoExprColumn,
    resolution: int,
) -> pl.Expr
```

Return the number of descendants at `resolution`.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"cell": ["8428347ffffffff"]})
df.select(child_count=plh3.cell_to_children_size("cell", resolution=5))
```

```text
shape: (1, 1)
┌─────────────┐
│ child_count │
│ ---         │
│ u64         │
╞═════════════╡
│ 7           │
└─────────────┘
```

## `cell_to_children`

```python
plh3.cell_to_children(cell: IntoExprColumn, resolution: int) -> pl.Expr
```

Return all descendants at `resolution` as a list.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"cell": ["8428347ffffffff"]})
df.select(children=plh3.cell_to_children("cell", resolution=5))
```

```text
shape: (1, 1)
┌───────────────────────────┐
│ children                  │
│ ---                       │
│ list[str]                 │
╞═══════════════════════════╡
│ ["85283463fffffff", "852… │
└───────────────────────────┘
```

## `cell_to_child_pos`

```python
plh3.cell_to_child_pos(cell: IntoExprColumn, resolution: int) -> pl.Expr
```

Return a cell's position within its ancestor at `resolution`.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"cell": ["85283473fffffff"]})
df.select(position=plh3.cell_to_child_pos("cell", resolution=4))
```

```text
shape: (1, 1)
┌──────────┐
│ position │
│ ---      │
│ u64      │
╞══════════╡
│ 4        │
└──────────┘
```

## `child_pos_to_cell`

```python
plh3.child_pos_to_cell(
    parent: IntoExprColumn,
    pos: IntoExprColumn,
    resolution: int,
) -> pl.Expr
```

Return the descendant at `resolution` identified by `pos` below `parent`.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {"parent": ["8428347ffffffff"], "position": [4]},
    schema_overrides={"position": pl.UInt64},
)
df.select(
    child=plh3.child_pos_to_cell("parent", "position", resolution=5)
)
```

```text
shape: (1, 1)
┌─────────────────┐
│ child           │
│ ---             │
│ str             │
╞═════════════════╡
│ 85283473fffffff │
└─────────────────┘
```

## `compact_cells`

```python
plh3.compact_cells(cells: IntoExprColumn) -> pl.Expr
```

Replace complete groups of same-resolution children with their parent cells.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {
        "cells": [[
            "85283463fffffff",
            "85283467fffffff",
            "8528346bfffffff",
            "8528346ffffffff",
            "85283473fffffff",
            "85283477fffffff",
            "8528347bfffffff",
        ]]
    }
)
df.select(compacted=plh3.compact_cells("cells"))
```

```text
shape: (1, 1)
┌─────────────────────┐
│ compacted           │
│ ---                 │
│ list[str]           │
╞═════════════════════╡
│ ["8428347ffffffff"] │
└─────────────────────┘
```

## `uncompact_cells`

```python
plh3.uncompact_cells(cells: IntoExprColumn, resolution: int) -> pl.Expr
```

Expand a compacted cell list to `resolution`.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"cells": [["8428347ffffffff"]]})
df.select(children=plh3.uncompact_cells("cells", resolution=5))
```

```text
shape: (1, 1)
┌───────────────────────────┐
│ children                  │
│ ---                       │
│ list[str]                 │
╞═══════════════════════════╡
│ ["85283463fffffff", "852… │
└───────────────────────────┘
```

!!! note "Resolution validation"

    Resolutions outside `0` through `15` raise `ValueError` while constructing
    the expression. Invalid parent/child relationships fail during evaluation.
