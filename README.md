

<p align="center">
 <img src="https://sergey-filimonov.nyc3.cdn.digitaloceanspaces.com/polars-h3/polars-h3-logo.webp"  />
</p>


This is a [Polars](https://docs.pola.rs/) extension that adds support for the [H3 discrete global grid system](https://github.com/uber/h3/), so you can index points and geometries to hexagons directly in Polars. All credits goes to the [h3o](https://github.com/HydroniumLabs/h3o) for doing the heavy lifting.

# Highlights

- 🚀 **Blazing Fast:** Built entirely in Rust, offering lightning-fast, multi-core H3 operations within Polars. Ideal for high-performance data processing.

- 🌍 **H3 Feature Parity:** Comprehensive support for H3 functions, covering almost everything the standard H3 library provides, excluding geometric functions.

- 🧩 **Seamless Integration:** Fully integrates with Polars.

- 📋 **Fully Tested:** Rigorously tested to ensure correctness.

# Get started

You can get started by installing it with pip (or [uv](https://github.com/astral-sh/uv)):
```bash
pip install polars-h3
```

You can use the extension as a drop-in replacement for the standard H3 functions.

```python
import polars_h3 as pl_h3
 
>>> df = pl.DataFrame(
...     {
...         "lat": [37.7749],
...         "long": [-122.4194],
...     }
... ).with_columns(
...     pl_h3.latlng_to_cell_string(
...         "lat",
...         "long",
...         7,
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

Check out the [quickstart notebook](notebooks/quickstart.ipynb) for more examples.

# Implemented functions

This extension implements most of the [H3 API](https://h3geo.org/docs/api/indexing). The full list of functions is below.

**Performance Note:** All functions support H3 indexes specified as `pl.UInt64` or `pl.Int64`,
but the unsigned one is preferred and is returned when the extension can't detect which
one to use. The unsigned and signed APIs are identical. All functions also support
`pl.Utf8` H3 index input and output.

We are unable to support the functions that work with geometries. 

### Full list of functions

✅ = Supported
🚧 = Pending
🛑 = Not supported

| Function | Description | Supported|
| --: | --- | ---|
| `latlng_to_cell` | Convert latitude/longitude coordinate to cell ID | ✅|
| `cell_to_lat` | Convert cell ID to latitude | ✅ |
| `cell_to_lng` | Convert cell ID to longitude | ✅ |
| `cell_to_latlng` | Convert cell ID to latitude/longitude | ✅ |
| `get_resolution` | Get resolution number of cell ID | ✅ |
| `str_to_int` | Convert VARCHAR cell ID to UBIGINT | ✅ |
| `int_to_str` | Convert BIGINT or UBIGINT cell ID to VARCHAR | ✅ |
| `is_valid_cell` | True if this is a valid cell ID | ✅ |
| `is_res_class_iii` | True if the cell's resolution is class III | ✅ |
| `is_pentagon` | True if the cell is a pentagon | ✅ |
| `get_icosahedron_faces` | List of icosahedron face IDs the cell is on | ✅ |
| `cell_to_parent` | Get coarser cell for a cell | ✅ |
| `cell_to_children` | Get finer cells for a cell | ✅ |
| `cell_to_center_child` | Provides the center child (finer) cell contained by cell at resolution childRes. | ✅ |
| `cell_to_child_pos` | Provides the position of the child cell within an ordered list of all children of the cell's parent at the specified resolution parentRes. The order of the ordered list is the same as that returned by cellToChildren. This is the complement of childPosToCell. | ✅ |
| `child_pos_to_cell` | Provides the child cell at a given position within an ordered list of all children of parent at the specified resolution childRes. The order of the ordered list is the same as that returned by cellToChildren. This is the complement of cellToChildPos. | ✅ |
| `compact_cells` | Compacts a collection of H3 cells by recursively replacing children cells with their parents if all children are present. Input cells must all share the same resolution. | ✅ |
| `uncompact_cells` | Uncompacts the set compactedSet of indexes to the resolution res. h3Set must be at least of size uncompactCellsSize(compactedSet, numHexes, res). | ✅ |
| `grid_ring` | Produces the "hollow ring" of cells which are exactly grid distance k from the origin cell | ✅ |
| `grid_disk` | Produces the "filled-in disk" of cells which are at most grid distance k from the origin cell. Output order is not guaranteed. | ✅ |
| `grid_path_cells` | Find a grid path to connect two cells | ✅ |
| `grid_distance` | Find the grid distance between two cells | ✅ |
| `cell_to_local_ij` | Convert a cell ID to a local I,J coordinate space | ✅|
| `local_ij_to_cell` | Convert a local I,J coordinate to a cell ID | ✅|
| `cell_to_vertex` | Get the vertex ID for a cell ID and vertex number |  ✅ |
| `cell_to_vertexes` | Get all vertex IDs for a cell ID | ✅|
| `vertex_to_latlng` | Convert a vertex ID to latitude/longitude coordinate | ✅ |
| `is_valid_vertex` | True if passed a valid vertex ID | ✅|
| `is_valid_directed_edge` | True if passed a valid directed edge ID | ✅ |
| `origin_to_directed_edges` | Get all directed edge IDs for a cell ID | ✅ |
| `directed_edge_to_cells` | Convert a directed edge ID to origin/destination cell IDs | ✅ |
| `get_directed_edge_origin` | Convert a directed edge ID to origin cell ID | ✅ |
| `get_directed_edge_destination` | Convert a directed edge ID to destination cell ID | ✅|
| `cells_to_directed_edge` | Convert an origin/destination pair to directed edge ID | ✅ |
| `are_neighbor_cells` | True if the two cell IDs are directly adjacent | ✅ |
| `average_hexagon_area` | Get average area of a hexagon cell at resolution |  ✅ |
| `cell_area` | Get the area of a cell ID |  ✅|
| `average_hexagon_edge_length` | Average hexagon edge length at resolution |  ✅|
| `edge_length` | Get the length of a directed edge ID |  🚧|
| `get_num_cells` | Get the number of cells at a resolution |  ✅|
| `get_res0_cells` | Get all resolution 0 cells |  🚧|
| `get_pentagons` | Get all pentagons at a resolution |  🚧|
| `great_circle_distance` | Compute the great circle distance between two points (haversine) |  ✅|
| `cells_to_multi_polygon_wkt` | Convert a set of cells to multipolygon WKT | 🛑 |
| `polygon_wkt_to_cells` | Convert polygon WKT to a set of cells | 🛑 |
| `cell_to_boundary_wkt` | Convert cell ID to cell boundary | 🛑 |
| `directed_edge_to_boundary_wkt` | Convert directed edge ID to linestring WKT | 🛑 |


> ⚠️ **Performance Note:** When possible, prefer using `pl.UInt64` for H3 indices instead of the UTF-8 hex string representation. String representations require casting operations which impact performance. Working directly with the native 64-bit integer format provides better computational efficiency.

Example:
```python
# Preferred: Using UInt64 representation
h3_indices = pl.Series([553270469932032, 553270469932033], dtype=pl.UInt64)

# Less performant: Using string representation
h3_indices = pl.Series(["85283473fffffff", "85283473fffffff"], dtype=pl.Utf8)
```