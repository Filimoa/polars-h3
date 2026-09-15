# Geometry

Turn polygon data into H3 cells directly in Polars. If your data has one area
per row—such as a census tract, delivery zone, or neighborhood—
`polygon_to_cells` adds the H3 cells that cover each area.

You do not need GeoPandas or a special Polars geometry type. The original
polygon and its attributes stay in the same row, so the result fits naturally
into an existing Polars pipeline.

## Read polygons from GeoParquet

GeoParquet is the shortest path. Read the file with Polars and pass its
geometry column—usually named `geometry`—to `polygon_to_cells`:

```python
import polars as pl
import polars_h3 as plh3

covered = (
    pl.scan_parquet("areas.parquet")
    .with_columns(
        h3_cells=plh3.polygon_to_cells("geometry", resolution=9)
    )
)
```

That is enough to go from stored polygons to H3 coverage. `covered` keeps every
source column and adds an `h3_cells` list to each row. Because this example uses
`scan_parquet`, it also stays lazy until you collect the result.

??? info "What are WKT and WKB?"

    They are two common ways to store geometry. WKT is readable text such as
    `POLYGON (...)`; WKB stores the same shape as compact bytes. GeoParquet
    normally uses WKB.

    `polygon_to_cells` accepts both: Polars `String` columns are read as WKT,
    and `Binary` columns are read as standard WKB or PostGIS EWKB. An explicit
    EWKB SRID must be 4326.

??? tip "Check the geometry column"

    WKB geometry must appear in Polars as `Binary`. GeoArrow native geometry
    encodings are not currently accepted. You can inspect a lazy input without
    loading the data:

    ```python
    schema = covered.collect_schema()
    assert schema["geometry"] == pl.Binary
    ```

## Read polygons from GeoJSON

Polars does not decode GeoJSON geometry by itself. Pyogrio can read the file
and hand the polygons to Polars as WKB:

```bash
uv add pyogrio pyarrow
```

```python
import pyogrio
import polars as pl
import polars_h3 as plh3

metadata, arrow_table = pyogrio.read_arrow("areas.geojson")
geometry_column = metadata["geometry_name"] or "wkb_geometry"

covered = pl.from_arrow(arrow_table).with_columns(
    h3_cells=plh3.polygon_to_cells(geometry_column, resolution=9)
)
```

The result has the same shape as the GeoParquet example: source attributes,
the original geometry, and one `h3_cells` list per polygon.

??? warning "Compatibility with Polars earlier than 1.36.0"

    [Polars 1.36.0 added Arrow extension-type support](https://github.com/pola-rs/polars/releases/tag/py-1.36.0).
    It loads Pyogrio's `geoarrow.wkb` geometry as its physical `Binary` storage
    type. With an earlier Polars release, remove the field annotation before
    converting the table if the GeoArrow extension type is reported as
    unsupported. The WKB bytes themselves are unchanged:

    ```python
    import pyarrow as pa

    geometry_index = arrow_table.schema.get_field_index(geometry_column)
    arrow_table = arrow_table.set_column(
        geometry_index,
        geometry_column,
        arrow_table[geometry_column].cast(pa.binary()),
    )

    covered = pl.from_arrow(arrow_table).with_columns(
        h3_cells=plh3.polygon_to_cells(geometry_column, resolution=9)
    )
    ```

## Work with the resulting cells

To produce one row per polygon/cell pair, explode the list:

```python
feature_cells = covered.explode("h3_cells")
```

### Distribute feature metrics across cells

To divide a metric such as census-tract population evenly across every H3
cell selected for that feature, divide by the list length before exploding.
Other feature columns are duplicated onto each resulting cell row:

```python
metric_columns = ["population"]

feature_cells = (
    covered
    .with_columns(cell_count=pl.col("h3_cells").list.len())
    .filter(pl.col("cell_count") > 0)
    .with_columns(
        [
            (pl.col(column) / pl.col("cell_count")).alias(column)
            for column in metric_columns
        ]
    )
    .explode("h3_cells")
    .rename({"h3_cells": "h3_cell"})
)
```

Overlapping source features can then be combined by cell:

```python
population_by_cell = (
    feature_cells
    .group_by("h3_cell")
    .agg(pl.col("population").sum())
)
```

This preserves each non-empty feature's metric total, apart from normal
floating-point rounding. It is an equal-allocation model, not areal
interpolation: cells are selected when their centroids lie inside the source
polygon, and every selected cell receives the same share. Features whose
coverage is empty at the chosen resolution are removed by the explicit
filter; use a finer resolution or define a fallback policy if those features
must be retained.

To visually compare the source polygons with their H3 coverage, pass the
row-aligned geometry and list columns directly to the optional Folium helper:

```bash
pip install folium
```

```python
coverage_frame = (
    covered.collect() if isinstance(covered, pl.LazyFrame) else covered
)
coverage_map = plh3.graphing.plot_polygon_coverage(
    coverage_frame,
    geometry_col=geometry_column,
    cells_col="h3_cells",
)
coverage_map
```

The helper accepts WKT or WKB geometry and scalar or list H3 cells. It draws
the source geometry and deduplicated cells as separate toggleable layers.

![A Houston census tract outlined in red with its resolution-9 H3 coverage shown as blue hexagons](../assets/polygon-coverage.png)

The example shows centroid-based coverage: selected cell boundaries may extend
beyond the source polygon. See the
[graphing reference](../graphing.md#plot_polygon_coverage) for null, scale, and
antimeridian behavior.

!!! warning "Coordinate reference system"

    H3 expects WGS84 longitude/latitude coordinates. `polygon_to_cells` parses
    geometry bytes or text but does not inspect GeoParquet CRS metadata or
    reproject coordinates. Reproject non-WGS84 data before this step.

## `polygon_to_cells`

```python
plh3.polygon_to_cells(
    geometry: IntoExprColumn,
    resolution: int,
) -> pl.Expr
```

Return every H3 cell whose centroid is inside each polygon or multipolygon.
Input may be WKB/EWKB `Binary` or WKT `String`. Explicit EWKB SRIDs must be
4326. Polygon holes and antimeridian-crossing geometries are supported. The
result has dtype `List(UInt64)`.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {
        "geometry": [
            "POLYGON((-122.42 37.77,-122.40 37.77,-122.40 37.79,"
            "-122.42 37.79,-122.42 37.77))"
        ]
    }
)

df.select(cells=plh3.polygon_to_cells("geometry", resolution=9))
```

Null input rows produce null output rows. Malformed WKT/WKB, non-polygon
geometry, and invalid polygon coordinates raise
`polars.exceptions.ComputeError`.

## `polygon_wkt_to_cells`

```python
plh3.polygon_wkt_to_cells(
    wkt: IntoExprColumn,
    resolution: int,
) -> pl.Expr
```

Compatibility wrapper for WKT inputs. New code should prefer
`polygon_to_cells`, which also accepts WKB `Binary` columns.

## `cells_to_multi_polygon_wkt`

```python
plh3.cells_to_multi_polygon_wkt(cells: IntoExprColumn) -> pl.Expr
```

Dissolve each list of H3 cells into one `MULTIPOLYGON` WKT string. Shared cell
edges are removed from the result. List elements may be `UInt64`, `Int64`, or
hexadecimal strings, but every row must contain unique cells at one resolution.

```python
df = pl.DataFrame(
    {"cells": [["8928308280fffff", "8928308280bffff"]]}
)

df.select(geometry=plh3.cells_to_multi_polygon_wkt("cells"))
```

An empty list produces `MULTIPOLYGON EMPTY`, and a null list produces null.
Invalid, duplicate, or mixed-resolution cells raise
`polars.exceptions.ComputeError`.

!!! warning "Coordinate order"

    WKT and WKB follow X/Y order: longitude first, then latitude. This differs
    from `cell_to_boundary`, which returns nested `[latitude, longitude]` lists.
