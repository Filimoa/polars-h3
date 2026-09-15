# Indexing

Convert coordinates to H3 cells and recover cell centers, boundaries, or local
IJ coordinates.

## `latlng_to_cell`

```python
plh3.latlng_to_cell(
    lat: IntoExprColumn,
    lng: IntoExprColumn,
    resolution: int,
    return_dtype: PolarsDataType = pl.UInt64,
) -> pl.Expr
```

Return the cell containing each latitude/longitude pair. `resolution` must be
from `0` through `15`; `return_dtype` can be `pl.UInt64`, `pl.Int64`, or
`pl.Utf8`.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"lat": [37.7749], "lng": [-122.4194]})
df.select(cell=plh3.latlng_to_cell("lat", "lng", resolution=7))
```

```text
shape: (1, 1)
┌────────────────────┐
│ cell               │
│ ---                │
│ u64                │
╞════════════════════╡
│ 608692970719281151 │
└────────────────────┘
```

## `cell_to_lat`

```python
plh3.cell_to_lat(cell: IntoExprColumn) -> pl.Expr
```

Return each cell center's latitude as `Float64`.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"cell": ["85283473fffffff"]})
df.select(latitude=plh3.cell_to_lat("cell"))
```

```text
shape: (1, 1)
┌───────────┐
│ latitude  │
│ ---       │
│ f64       │
╞═══════════╡
│ 37.345793 │
└───────────┘
```

## `cell_to_lng`

```python
plh3.cell_to_lng(cell: IntoExprColumn) -> pl.Expr
```

Return each cell center's longitude as `Float64`.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"cell": ["85283473fffffff"]})
df.select(longitude=plh3.cell_to_lng("cell"))
```

```text
shape: (1, 1)
┌─────────────┐
│ longitude   │
│ ---         │
│ f64         │
╞═════════════╡
│ -121.976376 │
└─────────────┘
```

## `cell_to_latlng`

```python
plh3.cell_to_latlng(cell: IntoExprColumn) -> pl.Expr
```

Return each cell center as `[latitude, longitude]`.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"cell": ["85283473fffffff"]})
df.select(center=plh3.cell_to_latlng("cell"))
```

```text
shape: (1, 1)
┌──────────────────────────┐
│ center                   │
│ ---                      │
│ list[f64]                │
╞══════════════════════════╡
│ [37.345793, -121.976376] │
└──────────────────────────┘
```

## `cell_to_boundary`

```python
plh3.cell_to_boundary(cell: IntoExprColumn) -> pl.Expr
```

Return boundary coordinates as `[[lat0, lng0], [lat1, lng1], ...]`.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"cell": ["85283473fffffff"]})
df.select(boundary=plh3.cell_to_boundary("cell"))
```

```text
shape: (1, 1)
┌───────────────────────────┐
│ boundary                  │
│ ---                       │
│ list[list[f64]]           │
╞═══════════════════════════╡
│ [[37.271356, -121.91508]… │
└───────────────────────────┘
```

## `cell_to_local_ij`

```python
plh3.cell_to_local_ij(
    cell: IntoExprColumn,
    origin: IntoExprColumn,
) -> pl.Expr
```

Return local `[i, j]` coordinates for `cell` relative to `origin`.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {
        "origin": ["85283473fffffff"],
        "cell": ["8528340bfffffff"],
    }
)
df.select(ij=plh3.cell_to_local_ij("cell", "origin"))
```

```text
shape: (1, 1)
┌──────────────┐
│ ij           │
│ ---          │
│ list[f64]    │
╞══════════════╡
│ [28.0, 15.0] │
└──────────────┘
```

## `local_ij_to_cell`

```python
plh3.local_ij_to_cell(
    origin: IntoExprColumn,
    i: IntoExprColumn,
    j: IntoExprColumn,
) -> pl.Expr
```

Return the cell at local coordinates `i`, `j` relative to `origin`.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {"origin": ["85283473fffffff"], "i": [28.0], "j": [15.0]}
)
df.select(cell=plh3.local_ij_to_cell("origin", "i", "j"))
```

```text
shape: (1, 1)
┌────────────────────┐
│ cell               │
│ ---                │
│ u64                │
╞════════════════════╡
│ 599686014516068351 │
└────────────────────┘
```

!!! note "Invalid inputs"

    Invalid resolutions or unsupported return dtypes raise `ValueError` while
    constructing the expression. Invalid indexes or local IJ transformations
    can raise a Polars `ComputeError` when evaluated.
