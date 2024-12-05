import polars as pl
import h3_polars
import time


# import time


num_vals = 10_000_000
df = pl.DataFrame(
    {
        "lat": [37.7749] * num_vals,
        "long": [-122.4194] * num_vals,
        # "res": [7] * num_vals,
    },
)
start = time.time()
result = df.with_columns(
    h3_cell=h3_polars.latlng_to_cell(
        pl.col("lat"),
        pl.col("long"),
        7,
    )
)
# print(result)
print(time.time() - start)
# Create exam
