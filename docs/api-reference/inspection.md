# Index inspection

Inspect, validate, and convert H3 indexes.

## `get_resolution`

```python
plh3.get_resolution(expr: IntoExprColumn) -> pl.Expr
```

Return the resolution, from `0` through `15`, of a cell, directed edge, or
vertex index.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"cell": ["85283473fffffff"]})
df.select(resolution=plh3.get_resolution("cell"))
```

```text
shape: (1, 1)
┌────────────┐
│ resolution │
│ ---        │
│ u32        │
╞════════════╡
│ 5          │
└────────────┘
```

## `str_to_int`

```python
plh3.str_to_int(expr: IntoExprColumn) -> pl.Expr
```

Parse hexadecimal H3 strings as `UInt64`. Invalid strings produce `null`.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"cell": ["85283473fffffff"]})
df.select(cell_int=plh3.str_to_int("cell"))
```

```text
shape: (1, 1)
┌────────────────────┐
│ cell_int           │
│ ---                │
│ u64                │
╞════════════════════╡
│ 599686042433355775 │
└────────────────────┘
```

## `int_to_str`

```python
plh3.int_to_str(expr: IntoExprColumn) -> pl.Expr
```

Format integer H3 indexes as canonical hexadecimal strings.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {"cell": [599686042433355775]}, schema={"cell": pl.UInt64}
)
df.select(cell_str=plh3.int_to_str("cell"))
```

```text
shape: (1, 1)
┌─────────────────┐
│ cell_str        │
│ ---             │
│ str             │
╞═════════════════╡
│ 85283473fffffff │
└─────────────────┘
```

## `is_valid_cell`

```python
plh3.is_valid_cell(expr: IntoExprColumn) -> pl.Expr
```

Return whether each value is a valid H3 cell.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"cell": ["85283473fffffff", "invalid"]})
df.select(valid=plh3.is_valid_cell("cell"))
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

## `is_pentagon`

```python
plh3.is_pentagon(expr: IntoExprColumn) -> pl.Expr
```

Return whether each valid cell is one of H3's 12 pentagons.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {"cell": [599686042433355775, 599119489002373119]},
    schema={"cell": pl.UInt64},
)
df.select(pentagon=plh3.is_pentagon("cell"))
```

```text
shape: (2, 1)
┌──────────┐
│ pentagon │
│ ---      │
│ bool     │
╞══════════╡
│ false    │
│ true     │
└──────────┘
```

## `is_res_class_III`

```python
plh3.is_res_class_III(expr: IntoExprColumn) -> pl.Expr
```

Return whether each cell uses a Class III resolution.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {"cell": ["85283473fffffff", "8428347ffffffff"]}
)
df.select(class_iii=plh3.is_res_class_III("cell"))
```

```text
shape: (2, 1)
┌───────────┐
│ class_iii │
│ ---       │
│ bool      │
╞═══════════╡
│ true      │
│ false     │
└───────────┘
```

## `get_icosahedron_faces`

```python
plh3.get_icosahedron_faces(expr: IntoExprColumn) -> pl.Expr
```

Return the icosahedron face numbers intersected by each cell.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"cell": ["85283473fffffff"]})
df.select(faces=plh3.get_icosahedron_faces("cell"))
```

```text
shape: (1, 1)
┌───────────┐
│ faces     │
│ ---       │
│ list[i64] │
╞═══════════╡
│ [7]       │
└───────────┘
```

For parent/child and compaction operations, see [Hierarchy](hierarchy.md).
