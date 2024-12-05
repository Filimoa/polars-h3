import polars as pl
import h3_polars
import time


# import time


# num_vals = int(1e7)
# print(f"num_vals: {num_vals:,}")
df = pl.DataFrame(
    {
        "lat": [37.7749],
        "long": [-122.4194],
        # "res": [7] * num_vals,
    },
).with_columns(
    h3_cell=h3_polars.latlng_to_cell_string(
        "lat",
        "long",
        7,
    ),
)
print(df)
# start = time.time()
# result = df.with_columns(
#     h3_cell=h3_polars.latlng_to_cell_string(
#         pl.col("lat"),
#         pl.col("long"),
#         7,
#     )
# )
# # print(result)
# print(time.time() - start)
# Create exam


df = (
    pl.DataFrame(
        {
            "h3_cell": ["8944ec60ba3ffff"] * 10,
        },
    )
    .with_columns(
        lat=h3_polars.cell_to_lat(pl.col("h3_cell")),
        lng=h3_polars.cell_to_lng(pl.col("h3_cell")),
        latlng=h3_polars.cell_to_latlng(pl.col("h3_cell")),
        res=h3_polars.get_resolution(pl.col("h3_cell")),
        int_cell=h3_polars.str_to_int(pl.col("h3_cell")),
        # str_cell=h3_polars.int_to_str(pl.col("int_cell")),
        is_valid=h3_polars.is_valid_cell(pl.col("h3_cell")),
    )
    .with_columns(
        str_cell=h3_polars.int_to_str(pl.col("int_cell")),
    )
)
print(df)


df = pl.DataFrame({"cell": ["8a1fb46622dffff", "821fb46622fffff"]}).with_columns(
    [
        pl.col("cell")
        .pipe(h3_polars.str_to_int)
        .pipe(h3_polars.is_pentagon)
        .alias("is_pent"),
        pl.col("cell")
        .pipe(h3_polars.str_to_int)
        .pipe(h3_polars.is_res_class_III)
        .alias("is_class3"),
        pl.col("cell")
        .pipe(h3_polars.str_to_int)
        .pipe(h3_polars.get_icosahedron_faces)
        .alias("faces"),
    ]
)
print(df)


df = pl.DataFrame(
    {
        "cell": ["8a1fb46622dffff"],
    }
).with_columns(
    [
        # Get parent
        pl.col("cell")
        .pipe(h3_polars.str_to_int)
        .pipe(h3_polars.cell_to_parent, resolution=9)
        .alias("parent"),
        # Get children
        pl.col("cell")
        .pipe(h3_polars.str_to_int)
        .pipe(h3_polars.cell_to_children, resolution=11)
        .alias("children"),
        # Get center child
        pl.col("cell")
        .pipe(h3_polars.str_to_int)
        .pipe(h3_polars.cell_to_center_child, resolution=11)
        .alias("center_child"),
    ]
)


print(df)


df = (
    pl.DataFrame({"origin": ["8a1fb46622dffff"], "destination": ["8a1fb46622d7fff"]})
    .with_columns(
        [
            # Get grid distance
            pl.col("origin").pipe(h3_polars.str_to_int).alias("origin_int"),
            pl.col("destination").pipe(h3_polars.str_to_int).alias("dest_int"),
        ]
    )
    .with_columns(
        [
            # Calculate grid distance
            h3_polars.grid_distance("origin_int", "dest_int").alias("distance"),
            # Get ring at k=2
            pl.col("origin_int").pipe(h3_polars.grid_ring, k=2).alias("ring"),
            # Get disk at k=2
            pl.col("origin_int").pipe(h3_polars.grid_disk, k=2).alias("disk"),
            # Get path between cells
            h3_polars.grid_path_cells("origin_int", "dest_int").alias("path"),
        ]
    )
)
print(df)


df = (
    pl.DataFrame({"cell": ["8a1fb46622dffff"]})
    .with_columns(
        [
            pl.col("cell").pipe(h3_polars.str_to_int).alias("cell_int"),
        ]
    )
    .with_columns(
        [
            # Get single vertex
            pl.col("cell_int")
            .pipe(h3_polars.cell_to_vertex, vertex_num=2)
            .alias("vertex"),
            # Get all vertexes
            pl.col("cell_int").pipe(h3_polars.cell_to_vertexes).alias("vertexes"),
            # Get vertex coordinates
            pl.col("cell_int")
            .pipe(h3_polars.cell_to_vertex, vertex_num=2)
            .pipe(h3_polars.vertex_to_latlng)
            .alias("vertex_coords"),
            # Validate vertex
            pl.col("cell_int")
            .pipe(h3_polars.cell_to_vertex, vertex_num=2)
            .pipe(h3_polars.is_valid_vertex)
            .alias("is_valid"),
        ]
    )
)
print(df)


df = (
    pl.DataFrame({"origin": ["8a1fb46622dffff"], "destination": ["8a1fb46622d7fff"]})
    .with_columns(
        [
            pl.col("origin").pipe(h3_polars.str_to_int).alias("origin_int"),
            pl.col("destination").pipe(h3_polars.str_to_int).alias("dest_int"),
        ]
    )
    .with_columns(
        [
            # Check if cells are neighbors
            h3_polars.are_neighbor_cells("origin_int", "dest_int").alias(
                "are_neighbors"
            ),
            # Get directed edge
            h3_polars.cells_to_directed_edge("origin_int", "dest_int").alias("edge"),
            # Get all edges from origin
            pl.col("origin_int")
            .pipe(h3_polars.origin_to_directed_edges)
            .alias("edges"),
            # Get edge boundary
            h3_polars.cells_to_directed_edge("origin_int", "dest_int")
            .pipe(h3_polars.directed_edge_to_boundary)
            .alias("boundary"),
        ]
    )
)
print(df)
