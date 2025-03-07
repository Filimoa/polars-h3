# Metrics

---

## `great_circle_distance`

Compute the Haversine distance between two latitude/longitude pairs.

```python
plh3.great_circle_distance(
    s_lat_deg: IntoExprColumn,
    s_lng_deg: IntoExprColumn,
    e_lat_deg: IntoExprColumn,
    e_lng_deg: IntoExprColumn,
    unit: Literal["km", "m"] = "km"
) -> pl.Expr
```

**Description**  
Uses the Haversine formula to approximate the great circle distance on Earth’s surface. The error is usually much smaller than 0.5% for typical use cases.

**Parameters**

- **s_lat_deg** : IntoExprColumn  
  Starting latitude in degrees (as `pl.Float64`).
- **s_lng_deg** : IntoExprColumn  
  Starting longitude in degrees (as `pl.Float64`).
- **e_lat_deg** : IntoExprColumn  
  Ending latitude in degrees (as `pl.Float64`).
- **e_lng_deg** : IntoExprColumn  
  Ending longitude in degrees (as `pl.Float64`).
- **unit** : `{"km", "m"}`  
  Unit of the returned distance. Defaults to kilometers.

**Returns**

- **Expr**  
  A Polars expression returning the great circle distance between the two points.

**Examples**

```python
df = pl.DataFrame({
    "start_lat": [37.775],
    "start_lng": [-122.419],
    "end_lat": [40.7128],
    "end_lng": [-74.0060],
})
df.with_columns(
    distance=plh3.great_circle_distance(
        "start_lat", "start_lng", "end_lat", "end_lng", unit="km"
    )
)
```

---

## `average_hexagon_area`

Return the average area of an H3 hexagon at a given resolution.

```python
plh3.average_hexagon_area(
    resolution: IntoExprColumn,
    unit: Literal["km^2", "m^2"] = "km^2"
) -> pl.Expr
```

**Parameters**

- **resolution** : IntoExprColumn  
  H3 resolution level (`0` to `15`).
- **unit** : `{"km^2", "m^2"}`  
  Unit of the returned area. Defaults to square kilometers (`"km^2"`).

**Returns**

- **Expr**  
  A Polars expression returning the average hexagon area at the given resolution.

**Examples**

```python
df = pl.DataFrame({"resolution": [5]})
df.with_columns(
    area=plh3.average_hexagon_area("resolution", "km^2")
)
```

---

## `cell_area`

Get the area of a specific H3 cell.

```python
plh3.cell_area(
    cell: IntoExprColumn,
    unit: Literal["km^2", "m^2"] = "km^2"
) -> pl.Expr
```

**Parameters**

- **cell** : IntoExprColumn  
  H3 cell index (as `pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
- **unit** : `{"km^2", "m^2"}`  
  Unit of the returned area. Defaults to square kilometers.

**Returns**

- **Expr**  
  A Polars expression returning the area of the H3 cell.

_Note:_ This function calls into a plugin that is elementwise. For invalid inputs, a `ComputeError` may be raised.

---

## `edge_length`

Determine the length of an H3 edge cell.

```python
plh3.edge_length(
    cell: IntoExprColumn,
    unit: Literal["km", "m"] = "km"
) -> pl.Expr
```

**Parameters**

- **cell** : IntoExprColumn  
  H3 index representing an edge (`pl.UInt64`, `pl.Int64`, or `pl.Utf8`).
- **unit** : `{"km", "m"}`  
  Unit of the returned length. Defaults to kilometers.

**Returns**

- **Expr**  
  Once implemented, it should return a Polars expression with the length of the edge.

---

## `average_hexagon_edge_length`

Get the average edge length of H3 hexagons at a specific resolution.

```python
plh3.average_hexagon_edge_length(
    resolution: IntoExprColumn,
    unit: Literal["km", "m"] = "km"
) -> pl.Expr
```

**Parameters**

- **resolution** : IntoExprColumn  
  H3 resolution level (`0` to `15`).
- **unit** : `{"km", "m"}`  
  Unit of the returned length. Defaults to kilometers.

**Returns**

- **Expr**  
  A Polars expression returning the average edge length for hexagons at the specified resolution.

**Examples**

```python
df = pl.DataFrame({"resolution": [1]})
df.with_columns(
    length=plh3.average_hexagon_edge_length("resolution", "km")
)
```

---

## `get_num_cells`

Get the total number of H3 cells at a given resolution.

```python
plh3.get_num_cells(
    resolution: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **resolution** : IntoExprColumn  
  H3 resolution level (`0` to `15`).

**Returns**

- **Expr**  
  A Polars expression returning the number of unique cells at the given resolution.

**Examples**

```python
df = pl.DataFrame({"resolution": [5]})
df.with_columns(
    count=plh3.get_num_cells("resolution")
)
```

---

## `get_pentagons`

Get the number of pentagons at a given resolution.

```python
plh3.get_pentagons(
    resolution: IntoExprColumn
) -> pl.Expr
```

**Parameters**

- **resolution** : IntoExprColumn  
  H3 resolution level (`0` to `15`).

**Returns**

- **Expr**  
  Once implemented, it should return a Polars expression with the count of pentagonal cells at the specified resolution.

---

**Note**

- Many of these functions will raise a `ComputeError` if given invalid input or null values.
- Functions requiring a specific `resolution` will also raise a `ValueError` for out-of-range resolutions (`< 0` or `> 15`).
- The `edge_length` and `get_pentagons` functions are placeholders that raise `NotImplementedError`.
