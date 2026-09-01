# Metrics

Measure spherical distances, areas, edge lengths, and grid size.

## `great_circle_distance`

```python
plh3.great_circle_distance(
    s_lat_deg: IntoExprColumn,
    s_lng_deg: IntoExprColumn,
    e_lat_deg: IntoExprColumn,
    e_lng_deg: IntoExprColumn,
    unit: Literal["km", "m"] = "km",
) -> pl.Expr
```

Return the spherical distance between two latitude-longitude pairs.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {
        "start_lat": [37.7749],
        "start_lng": [-122.4194],
        "end_lat": [40.7128],
        "end_lng": [-74.0060],
    }
)
df.select(
    distance_km=plh3.great_circle_distance(
        "start_lat", "start_lng", "end_lat", "end_lng"
    )
)
```

```text
shape: (1, 1)
┌─────────────┐
│ distance_km │
│ ---         │
│ f64         │
╞═════════════╡
│ 4130.382378 │
└─────────────┘
```

## `average_hexagon_area`

```python
plh3.average_hexagon_area(
    resolution: IntoExprColumn,
    unit: Literal["km^2", "m^2"] = "km^2",
) -> pl.Expr
```

Return the average area of a hexagon at each resolution.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"resolution": [5]})
df.select(area_km2=plh3.average_hexagon_area("resolution"))
```

```text
shape: (1, 1)
┌────────────┐
│ area_km2   │
│ ---        │
│ f64        │
╞════════════╡
│ 252.903858 │
└────────────┘
```

## `cell_area`

```python
plh3.cell_area(
    cell: IntoExprColumn,
    unit: Literal["km^2", "m^2"] = "km^2",
) -> pl.Expr
```

Return the spherical area of each cell.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {"cell": [599686042433355775]},
    schema_overrides={"cell": pl.UInt64},
)
df.select(area_km2=plh3.cell_area("cell"))
```

```text
shape: (1, 1)
┌────────────┐
│ area_km2   │
│ ---        │
│ f64        │
╞════════════╡
│ 265.092558 │
└────────────┘
```

## `edge_length`

```python
plh3.edge_length(
    cell: IntoExprColumn,
    unit: Literal["km", "m"] = "km",
) -> pl.Expr
```

Return the spherical length of each directed edge.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {"edge": [1608492358964346879]},
    schema_overrides={"edge": pl.UInt64},
)
df.select(length_km=plh3.edge_length("edge"))
```

```text
shape: (1, 1)
┌───────────┐
│ length_km │
│ ---       │
│ f64       │
╞═══════════╡
│ 10.30293  │
└───────────┘
```

## `average_hexagon_edge_length`

```python
plh3.average_hexagon_edge_length(
    resolution: IntoExprColumn,
    unit: Literal["km", "m"] = "km",
) -> pl.Expr
```

Return the average edge length of a hexagon at each resolution.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"resolution": [5]})
df.select(length_km=plh3.average_hexagon_edge_length("resolution"))
```

```text
shape: (1, 1)
┌───────────┐
│ length_km │
│ ---       │
│ f64       │
╞═══════════╡
│ 8.544     │
└───────────┘
```

## `get_num_cells`

```python
plh3.get_num_cells(resolution: IntoExprColumn) -> pl.Expr
```

Return the number of H3 cells at each resolution.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"resolution": [5]})
df.select(cells=plh3.get_num_cells("resolution"))
```

```text
shape: (1, 1)
┌─────────┐
│ cells   │
│ ---     │
│ u64     │
╞═════════╡
│ 2016842 │
└─────────┘
```

## `get_pentagons`

```python
plh3.get_pentagons(resolution: IntoExprColumn) -> pl.Expr
```

Return the 12 pentagons at each resolution.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame({"resolution": [5]})
df.select(pentagons=plh3.get_pentagons("resolution"))
```

```text
shape: (1, 1)
┌───────────────────────────┐
│ pentagons                 │
│ ---                       │
│ list[u64]                 │
╞═══════════════════════════╡
│ [599119489002373119, 599… │
└───────────────────────────┘
```

!!! note "Units"

    Distance functions accept `"km"` or `"m"`. Area functions accept `"km^2"`
    or `"m^2"`.
