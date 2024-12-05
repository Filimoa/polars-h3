import polars as pl
import h3_polars

import polars as pl
import h3_polars

# Test with some data
df = pl.DataFrame(
    {"lat": [37.7749], "lng": [-122.4194], "res": [7]},
)
result = df.with_columns(
    h3_cell=h3_polars.latlng_to_cell(
        pl.col("lat"),
        pl.col("lng"),
        7,
        # pl.col("res"),
        # resolution=7,
    )
)
print(result)

# Create example DataFrame with lat/lng columns
# df = pl.DataFrame(
#     {
#         "lat": [37.769377, 37.770381, 37.771385],
#         "lng": [-122.388903, -122.389907, -122.390911],
#     }
# )


# # Create a sample DataFrame with H3 cells
# # Using actual H3 cell IDs from San Francisco locations
# df = pl.DataFrame(
#     {
#         "location": ["SF Financial District", "Fisherman's Wharf", "Golden Gate Park"],
#         "h3_cell": [
#             0x8928308280FFFFF,  # Financial District
#             0x8928308283FFFFF,  # Fisherman's Wharf
#             0x89283082ABFFFFF,  # Golden Gate Park
#         ],
#     }
# )

# Convert H3 cells to latitude
# result = df.with_columns(latitude=h3_polars.h3_cell_to_lat("h3_cell"))

# print("H3 cells with their latitudes:")
# print(result)

# # Test with some edge cases
# edge_cases = pl.DataFrame(
#     {
#         "case": ["Valid Cell", "Invalid Cell", "Null"],
#         "h3_cell": [0x8928308280FFFFF, 0, None],
#     }
# )

# print("\nTesting edge cases:")
# print(edge_cases.with_columns(latitude=h3_polars.h3_cell_to_lat("h3_cell")))
