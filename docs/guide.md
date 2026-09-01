# User guide

Polars H3 is intentionally small: it exposes H3 operations as Polars
expressions. Most usage comes down to choosing an index representation and the
right function family.

## Expressions first

Functions accept column names or Polars expressions and return `pl.Expr`.
This makes them usable in eager and lazy pipelines without Python row loops.

```python
df.select(
    plh3.get_resolution("h3_cell").alias("resolution"),
    plh3.is_pentagon("h3_cell").alias("is_pentagon"),
)
```

Use aliases when you want stable, descriptive output column names.

## H3 index representations

Cell, directed-edge, and vertex functions generally accept these
representations:

| Representation | Polars dtype | Use it when… |
| --- | --- | --- |
| Unsigned integer | `pl.UInt64` | You are building an internal data pipeline or chaining H3 operations. |
| Signed integer | `pl.Int64` | An existing schema requires signed 64-bit integers. |
| String | `pl.Utf8` / `pl.String` | You are reading, displaying, or exchanging canonical hexadecimal H3 IDs. |

Prefer `UInt64` for computation. Convert at boundaries with
[`str_to_int`](api-reference/inspection.md#str_to_int) and
[`int_to_str`](api-reference/inspection.md#int_to_str).

## Resolutions

H3 resolutions range from 0 to 15. A higher resolution produces smaller cells.
Functions that move through the hierarchy require a valid target resolution;
see each function's reference entry for whether invalid input produces `null`
or an error.

```python
df.with_columns(
    parent=plh3.cell_to_parent("h3_cell", resolution=5),
    children=plh3.cell_to_children("h3_cell", resolution=9),
)
```

## Lists returned by H3 operations

Traversal, hierarchy, boundary, and vertex operations can return Polars list
columns. Keep them as lists for per-row processing, or use `explode` when each
item should become a row:

```python
neighbors = (
    df.select(plh3.grid_disk("h3_cell", 1).alias("neighbor"))
    .explode("neighbor")
)
```

## Optional graphing

Graphing helpers import Folium and Matplotlib only when needed. Install them
separately, then see the [graphing guide](graphing.md):

```bash
pip install folium matplotlib
```
