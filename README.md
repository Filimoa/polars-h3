# h3-polars

This is a [Polars](https://docs.pola.rs/) extension that adds support for the [H3 discrete global grid system](https://github.com/uber/h3/), so you can index points and geometries to hexagons in SQL.

# Get started

Load from the [community extensions repository](https://community-extensions.duckdb.org/extensions/h3.html):
```SQL
INSTALL h3 FROM community;
LOAD h3;
```

Test running an H3 function:
```SQL
SELECT h3_cell_to_latlng('822d57fffffffff');
```

Or, using the integer API, which generally has better performance:
```SQL
SELECT h3_cell_to_latlng(586265647244115967);
```

# Implemented functions

This extension implements the entire [H3 API](https://h3geo.org/docs/api/indexing). The full list of functions is below.

All functions support H3 indexes specified as `UBIGINT` (`uint64`) or `BIGINT` (`int64`),
but the unsigned one is preferred and is returned when the extension can't detect which
one to use. The unsigned and signed APIs are identical. All functions also support
`VARCHAR` H3 index input and output.

### Full list of functions

Here's the updated table with an additional column, **Supported**, which indicates whether each function is supported or not.  

| Function | Description | Supported
| --: | --- | ---
| `latlng_to_cell` | Convert latitude/longitude coordinate to cell ID | ✅
| `h3_latlng_to_cell_string` | Convert latitude/longitude coordinate to cell ID (returns VARCHAR) | 🕥
| `h3_cell_to_lat` | Convert cell ID to latitude | 🕥
| `h3_cell_to_lng` | Convert cell ID to longitude | 🕥
| `h3_cell_to_latlng` | Convert cell ID to latitude/longitude | 🕥
| `h3_cell_to_boundary_wkt` | Convert cell ID to cell boundary | 🕥
| `h3_get_resolution` | Get resolution number of cell ID | 🕥
| `h3_get_base_cell_number` | Get base cell number of cell ID | 🕥
| `h3_string_to_h3` | Convert VARCHAR cell ID to UBIGINT | 🕥
| `h3_h3_to_string` | Convert BIGINT or UBIGINT cell ID to VARCHAR | 🕥
| `h3_is_valid_cell` | True if this is a valid cell ID | 🕥
| `h3_is_res_class_iii` | True if the cell's resolution is class III | 🕥
| `h3_is_pentagon` | True if the cell is a pentagon | 🕥
| `h3_get_icosahedron_faces` | List of icosahedron face IDs the cell is on | 🕥
| `h3_cell_to_parent` | Get coarser cell for a cell | 🕥
| `h3_cell_to_children` | Get finer cells for a cell | 🕥
| `h3_cell_to_center_child` | Get the center finer cell for a cell | 🕥
| `h3_cell_to_child_pos` | Get a sub-indexing number for a cell inside a parent | 🕥
| `h3_child_pos_to_cell` | Convert parent and sub-indexing number to a cell ID | 🕥
| `h3_compact_cells` | Convert a set of single-resolution cells to the minimal mixed-resolution set | 🕥
| `h3_uncompact_cells` | Convert a mixed-resolution set to a single-resolution set of cells | 🕥
| `h3_grid_disk` | Find cells within a grid distance | 🕥
| `h3_grid_disk_distances` | Find cells within a grid distance, sorted by distance | 🕥
| `h3_grid_disk_unsafe` | Find cells within a grid distance, with no pentagon distortion | 🕥
| `h3_grid_disk_distances_unsafe` | Find cells within a grid distance, sorted by distance, with no pentagon distortion | 🕥
| `h3_grid_disk_distances_safe` | Find cells within a grid distance, sorted by distance | 🕥
| `h3_grid_ring_unsafe` | Find cells exactly a grid distance away, with no pentagon distortion | 🕥
| `h3_grid_path_cells` | Find a grid path to connect two cells | 🕥
| `h3_grid_distance` | Find the grid distance between two cells | 🕥
| `h3_cell_to_local_ij` | Convert a cell ID to a local I,J coordinate space | 🕥
| `h3_local_ij_to_cell` | Convert a local I,J coordinate to a cell ID | 🕥
| `h3_cell_to_vertex` | Get the vertex ID for a cell ID and vertex number | 🕥
| `h3_cell_to_vertexes` | Get all vertex IDs for a cell ID | 🕥
| `h3_vertex_to_lat` | Convert a vertex ID to latitude | 🕥
| `h3_vertex_to_lng` | Convert a vertex ID to longitude | 🕥
| `h3_vertex_to_latlng` | Convert a vertex ID to latitude/longitude coordinate | 🕥
| `h3_is_valid_vertex` | True if passed a valid vertex ID | 🕥
| `h3_is_valid_directed_edge` | True if passed a valid directed edge ID | 🕥
| `h3_origin_to_directed_edges` | Get all directed edge IDs for a cell ID | 🕥
| `h3_directed_edge_to_cells` | Convert a directed edge ID to origin/destination cell IDs | 🕥
| `h3_get_directed_edge_origin` | Convert a directed edge ID to origin cell ID | 🕥
| `h3_get_directed_edge_destination` | Convert a directed edge ID to destination cell ID | 🕥
| `h3_cells_to_directed_edge` | Convert an origin/destination pair to directed edge ID | 🕥
| `h3_are_neighbor_cells` | True if the two cell IDs are directly adjacent | 🕥
| `h3_directed_edge_to_boundary_wkt` | Convert directed edge ID to linestring WKT | 🕥
| `h3_get_hexagon_area_avg` | Get average area of a hexagon cell at resolution | 🕥
| `h3_cell_area` | Get the area of a cell ID | 🕥
| `h3_get_hexagon_edge_length_avg` | Average hexagon edge length at resolution | 🕥
| `h3_edge_length` | Get the length of a directed edge ID | 🕥
| `h3_get_num_cells` | Get the number of cells at a resolution | 🕥
| `h3_get_res0_cells` | Get all resolution 0 cells | 🕥
| `h3_get_res0_cells_string` | Get all resolution 0 cells (returns VARCHAR) | 🕥
| `h3_get_pentagons` | Get all pentagons at a resolution | 🕥
| `h3_get_pentagons_string` | Get all pentagons at a resolution (returns VARCHAR) | 🕥
| `h3_great_circle_distance` | Compute the great circle distance between two points (haversine) | 🕥
| `h3_cells_to_multi_polygon_wkt` | Convert a set of cells to multipolygon WKT | 🕥
| `h3_polygon_wkt_to_cells` | Convert polygon WKT to a set of cells | 🕥
