<p align="center">
 <img src="https://sergey-filimonov.nyc3.cdn.digitaloceanspaces.com/polars-h3/polars-h3-logo.webp"  />
</p>

This is a [Polars](https://docs.pola.rs/) extension that adds support for the [H3 discrete global grid system](https://github.com/uber/h3/), so you can index points and geometries to hexagons directly in Polars. All credits goes to the [h3o](https://github.com/HydroniumLabs/h3o) for doing the heavy lifting.

<div align="left">
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License"/>
  </a>
  <a href="https://pypi.org/project/polars-h3/">
    <img src="https://img.shields.io/pypi/v/polars-h3.svg" alt="PyPI Latest Release"/>
  </a>
</div>

# Highlights

- 🚀 **Blazing Fast:** Built entirely in Rust, offering vectorized, multi-core H3 operations within Polars. Ideal for high-performance data processing.

  - 25X faster than [h3-py](https://github.com/uber/h3-py)
  - 5X faster than [H3 DuckDB](https://github.com/isaacbrodsky/h3-duckdb) _(See [notebook](notebooks/benchmarking.ipynb) for more details)_

- 🌍 **H3 Feature Parity:** Comprehensive support for H3 functions, covering almost everything the standard H3 library provides, excluding geometric functions.

- 📋 **Fully Tested & Used in Production:** Thoroughly tested against the standard H3 library.

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

df = (
    pl.DataFrame(
        {
            "lat": [37.7749],
            "long": [-122.4194],
        }
    )
    .with_columns(
        plh3.latlng_to_cell(
            "lat",
            "long",
            resolution=7,
            return_dtype=pl.Utf8,
        ).alias("h3_cell")
    )
)

print(df)
```

```text
shape: (1, 3)
┌─────────┬───────────┬─────────────────┐
│ lat     ┆ long      ┆ h3_cell         │
│ ---     ┆ ---       ┆ ---             │
│ f64     ┆ f64       ┆ str             │
╞═════════╪═══════════╪═════════════════╡
│ 37.7749 ┆ -122.4194 ┆ 872830828ffffff │
└─────────┴───────────┴─────────────────┘
```

Check out the [quickstart notebook](notebooks/quickstart.ipynb) for more examples.

🌟 You can also find the advanced notebooks [here](notebooks/).

# Implemented functions

This extension implements most of the [H3 API](https://h3geo.org/docs/api/indexing). The full list of functions is below - you can find full docs [here](https://filimoa.github.io/polars-h3/).

> ⚠️ **Performance Note:** When possible, prefer using `pl.UInt64` for H3 indices instead of the `pl.Utf8` representation. String representations require casting operations which impact performance. Working directly with the native 64-bit integer format provides better computational efficiency.

We are unable to support the functions that work with geometries.

### Full list of functions

✅ = Supported
🚧 = Pending
🛑 = Not supported

| Function                                                                                                                 | Description                                                                                                              | Supported |
| :----------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------- | :-------- |
| [`latlng_to_cell`](https://filimoa.github.io/polars-h3/api-reference/indexing/#latlng_to_cell)                           | Convert latitude/longitude coordinate to cell ID                                                                         | ✅        |
| [`cell_to_lat`](https://filimoa.github.io/polars-h3/api-reference/indexing/#cell_to_lat)                                 | Convert cell ID to latitude                                                                                              | ✅        |
| [`cell_to_lng`](https://filimoa.github.io/polars-h3/api-reference/indexing/#cell_to_lng)                                 | Convert cell ID to longitude                                                                                             | ✅        |
| [`cell_to_latlng`](https://filimoa.github.io/polars-h3/api-reference/indexing/#cell_to_latlng)                           | Convert cell ID to latitude/longitude                                                                                    | ✅        |
| [`get_resolution`](https://filimoa.github.io/polars-h3/api-reference/inspection/#get_resolution)                         | Get resolution number of cell ID                                                                                         | ✅        |
| [`str_to_int`](https://filimoa.github.io/polars-h3/api-reference/inspection/#str_to_int)                                 | Convert `pl.Utf8` cell ID to `pl.UInt64`                                                                                 | ✅        |
| [`int_to_str`](https://filimoa.github.io/polars-h3/api-reference/inspection/#int_to_str)                                 | Convert `pl.UInt64` or `pl.Int64` cell ID to `pl.Utf8`                                                                   | ✅        |
| [`is_valid_cell`](https://filimoa.github.io/polars-h3/api-reference/inspection/#is_valid_cell)                           | True if this is a valid cell ID                                                                                          | ✅        |
| [`is_res_class_iii`](https://filimoa.github.io/polars-h3/api-reference/inspection/#is_res_class_iii)                     | True if the cell's resolution is class III                                                                               | ✅        |
| [`is_pentagon`](https://filimoa.github.io/polars-h3/api-reference/inspection/#is_pentagon)                               | True if the cell is a pentagon                                                                                           | ✅        |
| [`get_icosahedron_faces`](https://filimoa.github.io/polars-h3/api-reference/inspection/#get_icosahedron_faces)           | List of icosahedron face IDs the cell is on                                                                              | ✅        |
| [`cell_to_parent`](https://filimoa.github.io/polars-h3/api-reference/inspection/#cell_to_parent)                         | Get coarser cell for a cell                                                                                              | ✅        |
| [`cell_to_children`](https://filimoa.github.io/polars-h3/api-reference/inspection/#cell_to_children)                     | Get finer cells for a cell                                                                                               | ✅        |
| [`cell_to_center_child`](https://filimoa.github.io/polars-h3/api-reference/inspection/#cell_to_center_child)             | Provides the center child (finer) cell contained by cell at resolution childRes.                                         | ✅        |
| [`cell_to_child_pos`](https://filimoa.github.io/polars-h3/api-reference/inspection/#cell_to_child_pos)                   | Position of the child cell within the ordered list of all children of its parent at the specified resolution             | ✅        |
| [`child_pos_to_cell`](https://filimoa.github.io/polars-h3/api-reference/inspection/#child_pos_to_cell)                   | Child cell at a given position within the ordered list of children for a specified parent/resolution                     | ✅        |
| [`compact_cells`](https://filimoa.github.io/polars-h3/api-reference/inspection/#compact_cells)                           | Compacts a collection of H3 cells (all same resolution) by replacing child cells with their parent if all children exist | ✅        |
| [`uncompact_cells`](https://filimoa.github.io/polars-h3/api-reference/inspection/#uncompact_cells)                       | Uncompacts a set of H3 cells to the resolution `res`                                                                     | ✅        |
| [`grid_ring`](https://filimoa.github.io/polars-h3/api-reference/traversal/#grid_ring)                                    | Produces the "hollow ring" of cells which are exactly grid distance k from the origin cell                               | ✅        |
| [`grid_disk`](https://filimoa.github.io/polars-h3/api-reference/traversal/#grid_disk)                                    | Produces the "filled-in disk" of cells at most grid distance k from the origin cell                                      | ✅        |
| [`grid_path_cells`](https://filimoa.github.io/polars-h3/api-reference/traversal/#grid_path_cells)                        | Find a grid path to connect two cells                                                                                    | ✅        |
| [`grid_distance`](https://filimoa.github.io/polars-h3/api-reference/traversal/#grid_distance)                            | Find the grid distance between two cells                                                                                 | ✅        |
| [`cell_to_local_ij`](https://filimoa.github.io/polars-h3/api-reference/indexing/#cell_to_local_ij)                       | Convert a cell ID to a local I,J coordinate space                                                                        | ✅        |
| [`local_ij_to_cell`](https://filimoa.github.io/polars-h3/api-reference/indexing/#local_ij_to_cell)                       | Convert a local I,J coordinate to a cell ID                                                                              | ✅        |
| [`cell_to_boundary`](https://filimoa.github.io/polars-h3/api-reference/indexing/#cell_to_boundary)                       | Convert cell ID to its boundary lat/lng coordinates                                                                      | ✅        |
| [`cell_to_vertex`](https://filimoa.github.io/polars-h3/api-reference/vertexes/#cell_to_vertex)                           | Get the vertex ID for a cell ID and vertex number                                                                        | ✅        |
| [`cell_to_vertexes`](https://filimoa.github.io/polars-h3/api-reference/vertexes/#cell_to_vertexes)                       | Get all vertex IDs for a cell ID (5 for pentagon, 6 for hex)                                                             | ✅        |
| [`vertex_to_latlng`](https://filimoa.github.io/polars-h3/api-reference/vertexes/#vertex_to_latlng)                       | Convert a vertex ID to latitude/longitude coordinates                                                                    | ✅        |
| [`is_valid_vertex`](https://filimoa.github.io/polars-h3/api-reference/vertexes/#is_valid_vertex)                         | True if passed a valid vertex ID                                                                                         | ✅        |
| [`is_valid_directed_edge`](https://filimoa.github.io/polars-h3/api-reference/edge/#is_valid_directed_edge)               | True if passed a valid directed edge ID                                                                                  | ✅        |
| [`origin_to_directed_edges`](https://filimoa.github.io/polars-h3/api-reference/edge/#origin_to_directed_edges)           | Get all directed edge IDs for a cell ID                                                                                  | ✅        |
| [`directed_edge_to_cells`](https://filimoa.github.io/polars-h3/api-reference/edge/#directed_edge_to_cells)               | Convert a directed edge ID to origin/destination cell IDs                                                                | ✅        |
| [`get_directed_edge_origin`](https://filimoa.github.io/polars-h3/api-reference/edge/#get_directed_edge_origin)           | Convert a directed edge ID to origin cell ID                                                                             | ✅        |
| [`get_directed_edge_destination`](https://filimoa.github.io/polars-h3/api-reference/edge/#get_directed_edge_destination) | Convert a directed edge ID to destination cell ID                                                                        | ✅        |
| [`cells_to_directed_edge`](https://filimoa.github.io/polars-h3/api-reference/edge/#cells_to_directed_edge)               | Convert an origin/destination pair to directed edge ID                                                                   | ✅        |
| [`are_neighbor_cells`](https://filimoa.github.io/polars-h3/api-reference/edge/#are_neighbor_cells)                       | True if the two cell IDs share an edge                                                                                   | ✅        |
| [`average_hexagon_area`](https://filimoa.github.io/polars-h3/api-reference/metrics/#average_hexagon_area)                | Get average area of a hexagon cell at resolution                                                                         | ✅        |
| [`cell_area`](https://filimoa.github.io/polars-h3/api-reference/metrics/#cell_area)                                      | Get the area of a cell ID                                                                                                | ✅        |
| [`average_hexagon_edge_length`](https://filimoa.github.io/polars-h3/api-reference/metrics/#average_hexagon_edge_length)  | Average hexagon edge length at resolution                                                                                | ✅        |
| [`edge_length`](https://filimoa.github.io/polars-h3/api-reference/metrics/#edge_length)                                  | Get the length of a directed edge ID                                                                                     | ✅        |
| [`get_num_cells`](https://filimoa.github.io/polars-h3/api-reference/metrics/#get_num_cells)                              | Get the number of cells at a resolution                                                                                  | ✅        |
| [`get_pentagons`](https://filimoa.github.io/polars-h3/api-reference/metrics/#get_pentagons)                              | Get all pentagons at a resolution                                                                                        | ✅        |
| [`great_circle_distance`](https://filimoa.github.io/polars-h3/api-reference/metrics/#great_circle_distance)              | Compute the great circle distance between two points (haversine)                                                         | ✅        |
| `cells_to_multi_polygon_wkt`                                                                                             | Convert a set of cells to multipolygon WKT                                                                               | 🛑        |
| `polygon_wkt_to_cells`                                                                                                   | Convert polygon WKT to a set of cells                                                                                    | 🛑        |
| `directed_edge_to_boundary_wkt`                                                                                          | Convert directed edge ID to linestring WKT                                                                               | 🛑        |

### Plotting

The library also comes with helper functions to plot hexes on a Folium map.

```python
import polars_h3 as plh3
import polars as pl

hex_map = plh3.graphing.plot_hex_outlines(df, "h3_cell")
display(hex_map)

# or if you have a metric to plot

hex_map = plh3.graphing.plot_hex_fills(df, "h3_cell", "metric_col")
display(hex_map)
```

![CleanShot 2024-12-08 at 00 26 22](https://github.com/user-attachments/assets/2e707bfc-1a29-43b5-9260-723d776e5dad)

### Development

It's recommended to use [uv](https://github.com/astral-sh/uv) to manage the extension's python dependencies. If you modify rust code, you will need to run `uv run maturin develop --uv` to see changes.

You can run test suite with `uv run pytest`. You can also run the docs locally with `uv run --group docs zensical serve`.

### Benchmarking

If you're looking to benchmark the performance of the extension, build the release version with `maturin develop --release --uv` and then run `uv run -m benchmarks.engine` (assuming you have the benchmark dependencies installed). Benchmarking with the development version will lead to misleading results.

```bash
# 1 – (build) compile the optimized Rust extension
uv run maturin develop --release --uv

# 2 – (run) execute the benchmark CLI
uv run h3-bench \
  --libraries plh3 duckdb h3_py \   # which back-ends to test (or “all”)
  --functions latlng_to_cell cell_to_parent \  # which functions to time (or “all”)
  --iterations 3 \                  # repetitions per test
  --fast-factor 4 \                 # divide default row-counts to speed things up
  --output results.json             # optional: dump raw results
```
