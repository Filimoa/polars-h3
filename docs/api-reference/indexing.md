# Indexing functions

These functions are used for finding the H3 cell index containing coordinates, and for finding the center and boundary of H3 cells.

---

## `latlng_to_cell`

Convert latitude/longitude coordinates to H3 cell indices.

```python
plh3.latlng_to_cell(
    lat: IntoExprColumn,
    lng: IntoExprColumn,
    resolution: HexResolution,
    return_dtype: type[pl.Utf8] | type[pl.UInt64] | type[pl.Int64] = pl.UInt64
) -> pl.Expr
```

**Parameters**

- **lat** : IntoExprColumn  
  Column/expression containing latitude values (as `pl.Float64`).
- **lng** : IntoExprColumn  
  Column/expression containing longitude values (as `pl.Float64`).
- **resolution** : int in `[0, 15]`  
  H3 resolution level.
- **return_dtype** : `pl.UInt64` | `pl.Int64` | `pl.Utf8`  
  Desired return type for the H3 index (defaults to `pl.UInt64`).

**Returns**

- **Expr**  
  A Polars expression returning H3 cell indices in the specified format.

**Examples**

```python
>>> df = pl.DataFrame({
...     "lat": [37.7752702151959],
...     "lng": [-122.418307270836]
... })
>>> df.with_columns(
...     h3_cell=plh3.latlng_to_cell("lat", "lng", resolution=9, return_dtype=pl.Utf8)
... )
shape: (1, 3)
┌──────────────────┬────────────────────┬──────────────────┐
│ lat              │ lng                │ h3_cell          │
│ ---              │ ---                │ ---              │
│ f64              │ f64                │ str              │
╞══════════════════╪════════════════════╪══════════════════╡
│ 37.7752702151959 │ -122.418307270836  │ 8928308280fffff   │
└──────────────────┴────────────────────┴──────────────────┘

>>> # Using integer output
>>> df.with_columns(
...     h3_cell=plh3.latlng_to_cell("lat", "lng", resolution=1, return_dtype=pl.UInt64)
... )
shape: (1, 3)
┌─────────┬──────────┬─────────────────────┐
│ lat     │ lng      │ h3_cell             │
│ ---     │ ---      │ ---                 │
│ f64     │ f64      │ u64                 │
╞═════════╪══════════╪═════════════════════╡
│ 0.0     │ 0.0      │ 583031433791012863  │
└─────────┴──────────┴─────────────────────┘
```

**Errors**

- `ValueError`: If the `resolution` is not in `[0, 15]`.
- `ComputeError`: If input coordinates contain null values or are otherwise invalid.

---

## `cell_to_lat`

Extract the latitude coordinate from H3 cell indices.

```python
plh3.cell_to_lat(
    cell: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **cell** : IntoExprColumn  
  Column/expression containing H3 cell indices (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

**Returns**

- **Expr**  
  A Polars expression returning latitude values as `Float64`.

**Examples**

```python
>>> df = pl.DataFrame({
...     "h3_cell": ["85283473fffffff"]
... })
>>> df.with_columns(
...     lat=plh3.cell_to_lat("h3_cell"),
...     lng=plh3.cell_to_lng("h3_cell")
... )
shape: (1, 3)
┌──────────────────┬─────────────────┬───────────────────┐
│ h3_cell          │ lat             │ lng               │
│ ---              │ ---             │ ---               │
│ str              │ f64             │ f64               │
╞══════════════════╪═════════════════╪═══════════════════╡
│ 85283473fffffff  │ 37.345793375368 │ -121.976375972551 │
└──────────────────┴─────────────────┴───────────────────┘

>>> # Works with integer representation too
>>> df = pl.DataFrame({"h3_cell": [599686042433355775]}, schema={"h3_cell": pl.UInt64})
>>> df.with_columns(
...     lat=plh3.cell_to_lat("h3_cell"),
...     lng=plh3.cell_to_lng("h3_cell")
... )
shape: (1, 3)
┌─────────────────────┬─────────────────┬───────────────────┐
│ h3_cell             │ lat             │ lng               │
│ ---                 │ ---             │ ---               │
│ u64                 │ f64             │ f64               │
╞═════════════════════╪═════════════════╪═══════════════════╡
│ 599686042433355775  │ 37.345793375368 │ -121.976375972551 │
└─────────────────────┴─────────────────┴───────────────────┘
```

---

## `cell_to_lng`

Extract the longitude coordinate from H3 cell indices.

```python
plh3.cell_to_lng(
    cell: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **cell** : IntoExprColumn  
  Column/expression containing H3 cell indices (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

**Returns**

- **Expr**  
  A Polars expression returning longitude values as `Float64`.

**Examples**

```python
>>> df = pl.DataFrame({
...     "h3_cell": ["85283473fffffff"]
... })
>>> df.with_columns(
...     lat=plh3.cell_to_lat("h3_cell"),
...     lng=plh3.cell_to_lng("h3_cell")
... )
shape: (1, 3)
┌──────────────────┬─────────────────┬───────────────────┐
│ h3_cell          │ lat             │ lng               │
│ ---              │ ---             │ ---               │
│ str              │ f64             │ f64               │
╞══════════════════╪═════════════════╪═══════════════════╡
│ 85283473fffffff  │ 37.345793375368 │ -121.976375972551 │
└──────────────────┴─────────────────┴───────────────────┘

>>> # Works with integer representation too
>>> df = pl.DataFrame({"h3_cell": [599686042433355775]}, schema={"h3_cell": pl.UInt64})
>>> df.with_columns(
...     lat=plh3.cell_to_lat("h3_cell"),
...     lng=plh3.cell_to_lng("h3_cell")
... )
shape: (1, 3)
┌─────────────────────┬─────────────────┬───────────────────┐
│ h3_cell             │ lat             │ lng               │
│ ---                 │ ---             │ ---               │
│ u64                 │ f64             │ f64               │
╞═════════════════════╪═════════════════╪═══════════════════╡
│ 599686042433355775  │ 37.345793375368 │ -121.976375972551 │
└─────────────────────┴─────────────────┴───────────────────┘
```

---

## `cell_to_latlng`

Convert H3 cells into a list of `[latitude, longitude]`.

```python
plh3.cell_to_latlng(
    cell: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **cell** : IntoExprColumn  
  Column/expression containing H3 cell indices (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

**Returns**

- **Expr**  
  A list of floats `[lat, lng]` for each H3 cell.

**Examples**

```python
>>> df = pl.DataFrame({"cell": ["85283473fffffff"]})
>>> df.select(plh3.cell_to_latlng("cell"))
shape: (1, 1)
┌─────────────────────────┐
│ cell_to_latlng          │
│ ---                     │
│ list[f64]               │
╞═════════════════════════╡
│ [37.3457934, -121.9763…]│
└─────────────────────────┘

>>> # Easily extract lat/lng as separate columns:
>>> df.select([
...     plh3.cell_to_latlng("cell").arr.get(0).alias("lat"),
...     plh3.cell_to_latlng("cell").arr.get(1).alias("lng"),
... ])
shape: (1, 2)
┌───────────┬───────────┐
│ lat       │ lng       │
│ ---       │ ---       │
│ f64       │ f64       │
╞═══════════╡═══════════╡
│ 37.345793…│ -121.9763…│
└───────────┴───────────┘
```

**Errors**

- `ComputeError`: If null or invalid H3 cell indices are encountered.

---

## `cell_to_local_ij`

Convert an H3 cell index into its local IJ coordinates relative to a given origin.

```python
plh3.cell_to_local_ij(
    cell: IntoExprColumn,
    origin: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **cell** : IntoExprColumn  
  H3 cell index to convert (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
- **origin** : IntoExprColumn  
  Origin H3 cell index in the local IJ space.

**Returns**

- **Expr**  
  A Polars expression returning a list `[i, j]` of integer coordinates.

**Examples**

```python
>>> df = pl.DataFrame({
...     "origin": [599686042433355775],
...     "cell": [599686042433355776]
... })
>>> df.select(plh3.cell_to_local_ij("cell", "origin"))
shape: (1, 1)
┌────────────────┐
│ cell_to_local_ij│
│ ---            │
│ list[i64]      │
╞════════════════╡
│ [0,1]          │
└────────────────┘
```

**Errors**

- `ComputeError`: If the inputs are invalid, null, or cannot be transformed.

---

## `local_ij_to_cell`

Convert local IJ coordinates back into an H3 cell index using a given origin.

```python
plh3.local_ij_to_cell(
    origin: IntoExprColumn,
    i: IntoExprColumn,
    j: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **origin** : IntoExprColumn  
  The H3 cell index defining the local IJ space.
- **i** : IntoExprColumn  
  The local i-coordinate (row).
- **j** : IntoExprColumn  
  The local j-coordinate (column).

**Returns**

- **Expr**  
  A Polars expression returning the corresponding H3 cell index.

**Examples**

```python
>>> df = pl.DataFrame({
...     "origin": [599686042433355775],
...     "i": [0],
...     "j": [1]
... })
>>> df.select(plh3.local_ij_to_cell("origin", "i", "j"))
shape: (1, 1)
┌─────────────────┐
│ local_ij_to_cell│
│ ---             │
│ u64             │
╞═════════════════╡
│ 599686042433355776 │
└─────────────────┘
```

**Errors**

- `ComputeError`: If null or invalid inputs are encountered, or the transformation cannot be performed.

---

## `cell_to_boundary`

Retrieve the polygon boundary coordinates of the given H3 cell.

```python
plh3.cell_to_boundary(
    cell: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **cell** : IntoExprColumn  
  H3 cell indices (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).

**Returns**

- **Expr**  
  A Polars expression returning a list of `Float64` values representing `[lat0, lng0, lat1, lng1, …]`.

**Examples**

```python
>>> df = pl.DataFrame({
...     "cell": ["8a1fb464492ffff"]
... })
>>> df.select(plh3.cell_to_boundary("cell"))
shape: (1, 1)
┌────────────────────────────────────┐
│ cell_to_boundary                  │
│ ---                                │
│ list[f64]                          │
╞════════════════════════════════════╡
│ [[50.99, -76.05], [48.29, -81.91...│
└────────────────────────────────────┘
```

**Errors**

- `ComputeError`: If null or invalid H3 cell indices are encountered.
