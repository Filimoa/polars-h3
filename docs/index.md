<p align="center">
 <img src="https://sergey-filimonov.nyc3.cdn.digitaloceanspaces.com/polars-h3/polars-h3-logo.webp"  />
</p>

This is a [Polars](https://docs.pola.rs/) extension that adds support for the [H3 discrete global grid system](https://github.com/uber/h3/), so you can index points and geometries to hexagons directly in Polars. All credits goes to the [h3o](https://github.com/HydroniumLabs/h3o) for doing the heavy lifting.

<div align="left">
  <a href="https://pypi.org/project/polars-h3/">
    <img src="https://img.shields.io/pypi/v/polars-h3.svg" alt="PyPi Latest Release"/>
  </a>
</div>

# Highlights

- 🚀 **Blazing Fast:** Built entirely in Rust, offering vectorized, multi-core H3 operations within Polars. Ideal for high-performance data processing.

  - 25X faster than [h3-py](https://github.com/uber/h3-py)
  - 5X faster than [H3 DuckDB](https://github.com/isaacbrodsky/h3-duckdb) _(See [notebook](https://github.com/Filimoa/polars-h3/blob/master/notebooks/benchmarking.ipynb) for more details)_

- 🌍 **H3 Feature Parity:** Comprehensive support for H3 functions, covering almost everything the standard H3 library provides, excluding geometric functions.

- 📋 **Fully Tested:** Accurately tested against the standard H3 library.

- 🔍 **Data Type Agnostic:** Supports string and integer H3 indexes natively, eliminating format conversion hassles.

# Get started

You can get started by installing it with pip (or [uv](https://github.com/astral-sh/uv)):

```bash
pip install polars-h3
```

You can use the extension as a drop-in replacement for the standard H3 functions.

```python
import polars_h3 as plh3
import polars as pl

>>> df = pl.DataFrame(
...     {
...         "lat": [37.7749],
...         "long": [-122.4194],
...     }
... ).with_columns(
...     plh3.latlng_to_cell(
...         "lat",
...         "long",
...         resolution=7,
...         return_dtype=pl.Utf8
...     ).alias("h3_cell"),
... )
>>> df
shape: (1, 3)
┌─────────┬───────────┬─────────────────┐
│ lat     ┆ long      ┆ h3_cell         │
│ ---     ┆ ---       ┆ ---             │
│ f64     ┆ f64       ┆ str             │
╞═════════╪═══════════╪═════════════════╡
│ 37.7749 ┆ -122.4194 ┆ 872830828ffffff │
└─────────┴───────────┴─────────────────┘
```

Check out the [quickstart notebook](https://github.com/Filimoa/polars-h3/blob/master/notebooks/quickstart.ipynb) for more examples.

You can also find the advanced notebooks [here](https://github.com/Filimoa/polars-h3/blob/master/notebooks/).

# Implemented functions

This extension implements most of the [H3 API](https://h3geo.org/docs/api/indexing). The full list of functions is below.

> ⚠️ **Performance Note:** When possible, prefer using `pl.UInt64` for H3 indices instead of the `pl.Utf8` representation. String representations require casting operations which impact performance. Working directly with the native 64-bit integer format provides better computational efficiency.

We are unable to support the functions that work with geometries.

### Full list of functions

✅ = Supported
🚧 = Pending
🛑 = Not supported

### Full list of functions

| Function                                                                               | Description                                                                                 | Supported          |
| :------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------ | :----------------- |
| [`latlng_to_cell`](api-reference/indexing.md#latlng_to_cell)                           | Convert latitude/longitude coordinates to an H3 cell index.                                 | ✅                 |
| [`cell_to_lat`](api-reference/indexing.md#cell_to_lat)                                 | Extract the latitude coordinate from H3 cell indices.                                       | ✅                 |
| [`cell_to_lng`](api-reference/indexing.md#cell_to_lng)                                 | Extract the longitude coordinate from H3 cell indices.                                      | ✅                 |
| [`cell_to_latlng`](api-reference/indexing.md#cell_to_latlng)                           | Convert H3 cells into a list of `[latitude, longitude]`.                                    | ✅                 |
| [`cell_to_local_ij`](api-reference/indexing.md#cell_to_local_ij)                       | Convert an H3 cell index into its local IJ coordinates, relative to a given origin.         | ✅                 |
| [`local_ij_to_cell`](api-reference/indexing.md#local_ij_to_cell)                       | Convert local IJ coordinates back into an H3 cell index.                                    | ✅                 |
| [`cell_to_boundary`](api-reference/indexing.md#cell_to_boundary)                       | Retrieve the polygon boundary coordinates of the given H3 cell.                             | ✅                 |
| [`are_neighbor_cells`](api-reference/edge.md#are_neighbor_cells)                       | Check if two H3 cells share a common edge.                                                  | ✅                 |
| [`cells_to_directed_edge`](api-reference/edge.md#cells_to_directed_edge)               | Create a directed H3 edge from two neighboring cells.                                       | ✅                 |
| [`is_valid_directed_edge`](api-reference/edge.md#is_valid_directed_edge)               | Check if an H3 index is a valid directed edge.                                              | ✅                 |
| [`directed_edge_to_cells`](api-reference/edge.md#directed_edge_to_cells)               | Retrieve the origin/destination cells from a directed edge.                                 | ✅                 |
| [`get_directed_edge_origin`](api-reference/edge.md#get_directed_edge_origin)           | Extract the origin cell from a directed H3 edge.                                            | ✅                 |
| [`get_directed_edge_destination`](api-reference/edge.md#get_directed_edge_destination) | Extract the destination cell from a directed H3 edge.                                       | ✅                 |
| [`origin_to_directed_edges`](api-reference/edge.md#origin_to_directed_edges)           | List all directed edges originating from a given cell.                                      | ✅                 |
| [`directed_edge_to_boundary`](api-reference/edge.md#directed_edge_to_boundary)         | Retrieve the geographic boundary (list of lat/lng pairs) for a directed edge.               | ✅                 |
| [`get_resolution`](api-reference/inspection.md#get_resolution)                         | Retrieve the resolution of H3 indices (cells, edges, or vertices).                          | ✅                 |
| [`str_to_int`](api-reference/inspection.md#str_to_int)                                 | Convert string-based H3 indices into `UInt64` representation.                               | ✅                 |
| [`int_to_str`](api-reference/inspection.md#int_to_str)                                 | Convert integer-based H3 indices into string form.                                          | ✅                 |
| [`is_valid_cell`](api-reference/inspection.md#is_valid_cell)                           | Check if H3 cell indices are valid.                                                         | ✅                 |
| [`is_pentagon`](api-reference/inspection.md#is_pentagon)                               | Determine if an H3 cell is a pentagon.                                                      | ✅                 |
| [`is_res_class_III`](api-reference/inspection.md#is_res_class_iii)                     | Check if H3 cells belong to Class III resolution.                                           | ✅                 |
| [`get_icosahedron_faces`](api-reference/inspection.md#get_icosahedron_faces)           | Retrieve the icosahedron faces intersected by an H3 cell.                                   | ✅                 |
| [`cell_to_parent`](api-reference/inspection.md#cell_to_parent)                         | Retrieve the parent cell of a given H3 cell at a specified resolution.                      | ✅                 |
| [`cell_to_center_child`](api-reference/inspection.md#cell_to_center_child)             | Retrieve the “center child” of an H3 cell at a finer resolution.                            | ✅                 |
| [`cell_to_children_size`](api-reference/inspection.md#cell_to_children_size)           | Get the number of child cells at a given resolution.                                        | ✅                 |
| [`cell_to_children`](api-reference/inspection.md#cell_to_children)                     | Retrieve all child cells at a specified resolution.                                         | ✅                 |
| [`cell_to_child_pos`](api-reference/inspection.md#cell_to_child_pos)                   | Get the position index of a child cell within its parent hierarchy.                         | ✅                 |
| [`child_pos_to_cell`](api-reference/inspection.md#child_pos_to_cell)                   | Get the child cell at a given position index for a specified parent/resolution.             | ✅                 |
| [`compact_cells`](api-reference/inspection.md#compact_cells)                           | Compact a set of H3 cells into a minimal covering set.                                      | ✅                 |
| [`uncompact_cells`](api-reference/inspection.md#uncompact_cells)                       | Uncompact a set of H3 cells to the specified resolution.                                    | ✅                 |
| [`great_circle_distance`](api-reference/metrics.md#great_circle_distance)              | Compute the Haversine distance between two sets of lat/lng coordinates.                     | ✅                 |
| [`average_hexagon_area`](api-reference/metrics.md#average_hexagon_area)                | Get the average area of an H3 hexagon at a given resolution.                                | ✅                 |
| [`cell_area`](api-reference/metrics.md#cell_area)                                      | Get the area of a specific H3 cell.                                                         | ✅                 |
| [`edge_length`](api-reference/metrics.md#edge_length)                                  | Get the length of an H3 edge cell (currently raises `NotImplementedError`).                 | 🚧                 |
| [`average_hexagon_edge_length`](api-reference/metrics.md#average_hexagon_edge_length)  | Get the average edge length for hexagons at a given resolution.                             | ✅                 |
| [`get_num_cells`](api-reference/metrics.md#get_num_cells)                              | Get the total number of H3 cells at a given resolution.                                     | ✅                 |
| [`get_pentagons`](api-reference/metrics.md#get_pentagons)                              | Get the number of pentagons at a given resolution (currently raises `NotImplementedError`). | 🚧                 |
| [`grid_distance`](api-reference/traversal.md#grid_distance)                            | Compute the grid distance (minimum steps) between two H3 cells.                             | ✅                 |
| [`grid_ring`](api-reference/traversal.md#grid_ring)                                    | Produce a “hollow ring” of cells at distance `k` from the origin cell.                      | ✅                 |
| [`grid_disk`](api-reference/traversal.md#grid_disk)                                    | Produce a “filled disk” of cells within distance `k` of an origin cell.                     | ✅                 |
| [`grid_path_cells`](api-reference/traversal.md#grid_path_cells)                        | Return the minimal path of cells connecting an origin and destination.                      | ✅                 |
| [`cell_to_vertex`](api-reference/vertexes.md#cell_to_vertex)                           | Retrieve the H3 vertex index for a specific vertex of a given cell.                         | ✅                 |
| [`cell_to_vertexes`](api-reference/vertexes.md#cell_to_vertexes)                       | Retrieve all vertex indices for a given H3 cell (5 for pentagon, 6 for hex).                | ✅                 |
| [`vertex_to_latlng`](api-reference/vertexes.md#vertex_to_latlng)                       | Convert an H3 vertex index into its latitude/longitude coordinates.                         | ✅                 |
| [`is_valid_vertex`](api-reference/vertexes.md#is_valid_vertex)                         | Check whether an H3 index represents a valid vertex.                                        | ✅                 |
| _`cells_to_multi_polygon_wkt`_                                                         | Convert a set of cells to multipolygon WKT.                                                 | 🛑 (Not supported) |
| _`polygon_wkt_to_cells`_                                                               | Convert polygon WKT to a set of cells.                                                      | 🛑 (Not supported) |
| _`directed_edge_to_boundary_wkt`_                                                      | Convert directed edge ID to linestring WKT.                                                 | 🛑 (Not supported) |

### Plotting

The library also comes with helper functions to plot hexes on a Folium map.

```python
import polars_h3 as pl_h3
import polars as pl

hex_map = pl_h3.graphing.plot_hex_outlines(df, "h3_cell")
display(hex_map)

# or if you have a metric to plot

hex_map = pl_h3.graphing.plot_hex_fills(df, "h3_cell", "metric_col")
display(hex_map)
```

![CleanShot 2024-12-08 at 00 26 22](https://github.com/user-attachments/assets/2e707bfc-1a29-43b5-9260-723d776e5dad)

### Development

It's recommended to use [uv](https://github.com/astral-sh/uv) to manage the extension dependencies. If you modify rust code, you will need to run `uv run maturin develop --uv` to see changes. If you're looking to benchmark the performance of the extension, build the release version with `maturin develop --release --uv` and then run `uv run -m benchmarks.engine` (assuming you have the benchmark dependencies installed). Benchmarking with the development version will lead to misleading results.
