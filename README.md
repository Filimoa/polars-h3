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

| Function | Description | Supported|
| --: | --- | ---|
| `latlng_to_cell` | Convert latitude/longitude coordinate to cell ID | ✅|
| `latlng_to_cell_string` | Convert latitude/longitude coordinate to cell ID (returns VARCHAR) | ✅ |
| `cell_to_lat` | Convert cell ID to latitude | ✅ |
| `cell_to_lng` | Convert cell ID to longitude | ✅ |
| `cell_to_latlng` | Convert cell ID to latitude/longitude | ✅ |
| `get_resolution` | Get resolution number of cell ID | ✅ |
| `get_base_cell_number` | Get base cell number of cell ID | 🕥|
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
| `h3_cell_to_local_ij` | Convert a cell ID to a local I,J coordinate space | 🕥|
| `h3_local_ij_to_cell` | Convert a local I,J coordinate to a cell ID | 🕥|
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
| `directed_edge_to_boundary_wkt` | Convert directed edge ID to linestring WKT | ✅ |
| `h3_get_hexagon_area_avg` | Get average area of a hexagon cell at resolution | 🕥|
| `h3_cell_area` | Get the area of a cell ID | 🕥|
| `h3_get_hexagon_edge_length_avg` | Average hexagon edge length at resolution | 🕥|
| `h3_edge_length` | Get the length of a directed edge ID | 🕥|
| `h3_get_num_cells` | Get the number of cells at a resolution | 🕥|
| `h3_get_res0_cells` | Get all resolution 0 cells | 🕥|
| `h3_get_res0_cells_string` | Get all resolution 0 cells (returns VARCHAR) | 🕥|
| `h3_get_pentagons` | Get all pentagons at a resolution | 🕥|
| `h3_get_pentagons_string` | Get all pentagons at a resolution (returns VARCHAR) | 🕥|
| `h3_great_circle_distance` | Compute the great circle distance between two points (haversine) | 🕥|
| `cells_to_multi_polygon_wkt` | Convert a set of cells to multipolygon WKT | 🛑 |
| `polygon_wkt_to_cells` | Convert polygon WKT to a set of cells | 🛑 |
| `cell_to_boundary_wkt` | Convert cell ID to cell boundary | 🛑 |
