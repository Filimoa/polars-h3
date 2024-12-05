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


df = pl.DataFrame(
    {
        "h3_cell": ["8944ec60ba3ffff"] * 10,
    },
).with_columns(
    lat=h3_polars.cell_to_lat(pl.col("h3_cell")),
    lng=h3_polars.cell_to_lng(pl.col("h3_cell")),
    latlng=h3_polars.cell_to_latlng(pl.col("h3_cell")),
)
print(df)
