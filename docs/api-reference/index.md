# API reference

All public H3 operations return Polars expressions and can be used in
`select`, `with_columns`, and lazy queries. Functions accept column names or
Polars expressions unless their signature documents a scalar argument.

| Family | Purpose | Reference |
| --- | --- | --- |
| Indexing | Convert coordinates, cells, local IJ coordinates, and boundaries. | [Indexing](indexing.md) |
| Geometry | Tile WKT/WKB polygons and dissolve cell sets into WKT. | [Geometry](geometry.md) |
| Index inspection | Validate, convert, and inspect H3 indexes. | [Index inspection](inspection.md) |
| Hierarchy | Navigate parent/child relationships and compact cell sets. | [Hierarchy](hierarchy.md) |
| Directed edges | Create and inspect edges between neighboring cells. | [Directed edges](edge.md) |
| Traversal | Measure grid distance and construct rings, disks, and paths. | [Traversal](traversal.md) |
| Vertices | Create, validate, and locate H3 vertices. | [Vertices](vertexes.md) |
| Metrics | Calculate areas, lengths, distances, and global cell counts. | [Metrics](metrics.md) |

For optional Folium helpers, see the separate [graphing reference](../graphing.md).

!!! note "Geometry representation"

    Geometry conversion accepts ordinary WKT `String` or WKB `Binary` columns.
    Geometry values exist only inside the Rust expression, so no Polars
    geometry dtype is required.
