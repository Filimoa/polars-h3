# import polars as pl
# import pytest
# import h3_polars


# def test_latlng_to_cell():
#     # Test invalid resolution
#     df = pl.DataFrame({"lat": [0.0], "lng": [0.0]})
#     result = df.with_columns(cell=h3_polars.latlng_to_cell("lat", "lng", -1))
#     assert result["cell"][0] is None

#     # Test valid resolution
#     result = df.with_columns(cell=h3_polars.latlng_to_cell("lat", "lng", 1))
#     assert result["cell"][0] == 583031433791012863

#     # Test null latitude
#     df = pl.DataFrame({"lat": [37.7752702151959], "lng": [None]})
#     result = df.with_columns(cell=h3_polars.latlng_to_cell("lat", "lng", 9))
#     assert result["cell"][0] is None

#     # Test specific coordinates
#     df = pl.DataFrame({"lat": [37.7752702151959], "lng": [-122.418307270836]})
#     result = df.with_columns(cell=h3_polars.latlng_to_cell("lat", "lng", 9))
#     assert hex(result["cell"][0])[2:] == "8928308280fffff"


# def test_latlng_to_cell_string():
#     # Test invalid resolution
#     df = pl.DataFrame({"lat": [0.0], "lng": [0.0]})
#     result = df.with_columns(cell=h3_polars.latlng_to_cell_string("lat", "lng", -1))
#     assert result["cell"][0] is None

#     # Test valid resolution
#     result = df.with_columns(cell=h3_polars.latlng_to_cell_string("lat", "lng", 1))
#     assert result["cell"][0] == "81757ffffffffff"

#     # Test null coordinates
#     df = pl.DataFrame({"lat": [37.7752702151959], "lng": [None]})
#     result = df.with_columns(cell=h3_polars.latlng_to_cell_string("lat", "lng", 9))
#     assert result["cell"][0] is None

#     # Test specific coordinates
#     df = pl.DataFrame({"lat": [37.7752702151959], "lng": [-122.418307270836]})
#     result = df.with_columns(cell=h3_polars.latlng_to_cell_string("lat", "lng", 9))
#     assert result["cell"][0] == "8928308280fffff"


# def test_cell_to_latlng():
#     # Test with string input
#     df = pl.DataFrame({"cell": ["85283473fffffff"]})

#     # Test individual lat/lng functions
#     result = df.with_columns(
#         lat=pl.col("cell").pipe(h3_polars.cell_to_lat),
#         lng=pl.col("cell").pipe(h3_polars.cell_to_lng),
#     )
#     assert pytest.approx(result["lat"][0]) == 37.34579337536848
#     assert pytest.approx(result["lng"][0]) == -121.9763759725512

#     # Test combined latlng function
#     result = df.with_columns(coords=h3_polars.cell_to_latlng("cell"))
#     assert pytest.approx(result["coords"][0][0]) == 37.34579337536848
#     assert pytest.approx(result["coords"][0][1]) == -121.9763759725512

#     # Test with integer input
#     df = df.with_columns(cell_int=h3_polars.str_to_int("cell"))
#     result = df.with_columns(
#         lat=pl.col("cell_int").pipe(h3_polars.cell_to_lat),
#         lng=pl.col("cell_int").pipe(h3_polars.cell_to_lng),
#     )
#     assert pytest.approx(result["lat"][0]) == 37.34579337536848
#     assert pytest.approx(result["lng"][0]) == -121.9763759725512

#     # Test invalid cell
#     df = pl.DataFrame({"cell": ["ffffffffffffffff"]})
#     result = df.with_columns(
#         lat=pl.col("cell").pipe(h3_polars.cell_to_lat),
#         lng=pl.col("cell").pipe(h3_polars.cell_to_lng),
#     )
#     assert result["lat"][0] is None
#     assert result["lng"][0] is None
