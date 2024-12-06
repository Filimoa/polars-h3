import pytest
import polars as pl
import polars_h3
from typing import Union, List, Dict


@pytest.mark.parametrize(
    "lat1, lng1, lat2, lng2, unit, expected_distance",
    [
        pytest.param(40.7128, -74.0060, 40.7128, -74.0060, "km", 0, id="same_point_km"),
        pytest.param(
            40.7128, -74.0060, 42.3601, -71.0589, "km", 306.108, id="diff_points_km"
        ),
        pytest.param(
            40.7128, -74.0060, 42.3601, -71.0589, "m", 306108, id="diff_points_m"
        ),
        pytest.param(
            40.7128,
            -74.0060,
            34.0522,
            -118.2437,
            "km",
            3936.155,
            id="large_distance_km",
        ),
        pytest.param(
            40.7128, -74.0060, 34.0522, -118.2437, "m", 3936155, id="large_distance_m"
        ),
    ],
)
def test_great_circle_distance(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
    unit: Union[str, None],
    expected_distance: Union[float, None],
):
    df = pl.DataFrame(
        {
            "lat1": [lat1],
            "lng1": [lng1],
            "lat2": [lat2],
            "lng2": [lng2],
        }
    ).with_columns(
        distance=polars_h3.great_circle_distance("lat1", "lng1", "lat2", "lng2", unit)
    )

    if expected_distance is None:
        assert df["distance"][0] is None
    else:
        assert pytest.approx(df["distance"][0], rel=1e-3) == expected_distance


@pytest.mark.parametrize(
    "resolution, unit, expected_area",
    [
        pytest.param(0, "km^2", 4357449.416078383, id="res0_km2"),
        pytest.param(1, "km^2", 609788.4417941332, id="res1_km2"),
        pytest.param(9, "m^2", 105332.51342720671, id="res0_m2"),
        pytest.param(10, "m^2", 15047.50190766435, id="res1_m2"),
        # pytest.param(-1, "km^2", None, id="invalid_res"), # should be able to handle, currently has silent strange behavior
    ],
)
def test_average_hexagon_area(
    resolution: int, unit: str, expected_area: Union[float, None]
):
    df = pl.DataFrame({"resolution": [resolution]}).with_columns(
        polars_h3.average_hexagon_area(pl.col("resolution"), unit).alias("area")
    )
    if expected_area is None:
        assert df["area"][0] is None
    else:
        assert pytest.approx(df["area"][0], rel=1e-2) == expected_area


@pytest.mark.parametrize(
    "h3_cell, schema, unit, expected_area",
    [
        pytest.param(
            "8928308280fffff", None, "km^2", 0.1093981886464832, id="string_km2"
        ),
        pytest.param(
            "8928308280fffff", None, "m^2", 109398.18864648319, id="string_m2"
        ),
        pytest.param(
            586265647244115967,
            {"h3_cell": pl.UInt64},
            "km^2",
            85321.69572540345,
            id="uint64_km2",
        ),
        pytest.param(
            586265647244115967,
            {"h3_cell": pl.Int64},
            "km^2",
            85321.69572540345,
            id="int64_km2",
        ),
        pytest.param("fffffffffffffff", None, "km^2", None, id="invalid_cell"),
    ],
)
def test_hexagon_area(
    h3_cell: Union[str, int],
    schema: Union[Dict[str, pl.DataType], None],
    unit: str,
    expected_area: Union[float, None],
):
    df = pl.DataFrame({"h3_cell": [h3_cell]}, schema=schema).with_columns(
        area=polars_h3.cell_area(pl.col("h3_cell"), unit)
    )
    if expected_area is None:
        assert df["area"][0] is None
    else:
        assert pytest.approx(df["area"][0], rel=1e-9) == expected_area


@pytest.mark.parametrize(
    "resolution, unit, expected_length",
    [
        pytest.param(0, "km", 1107.712591, id="res0_km"),
        pytest.param(1, "km", 418.6760055, id="res1_km"),
        pytest.param(0, "m", 1107712.591, id="res0_m"),
        pytest.param(1, "m", 418676.0, id="res1_m"),
        # pytest.param(-1, "km", None, id="invalid_res"),
    ],
)
def test_average_hexagon_edge_length(
    resolution: int, unit: str, expected_length: Union[float, None]
):
    df = pl.DataFrame({"resolution": [resolution]}).with_columns(
        length=polars_h3.average_hexagon_edge_length(pl.col("resolution"), unit)
    )
    if expected_length is None:
        assert df["length"][0] is None
    else:
        assert pytest.approx(df["length"][0], rel=1e-3) == expected_length


# @pytest.mark.parametrize(
#     "h3_cell, schema, unit, expected_length",
#     [
#         pytest.param("115283473fffffff", None, "km", 10.294, id="string_km"),
#         pytest.param("115283473fffffff", None, "m", 10294.736, id="string_m"),
#         pytest.param(
#             1608492358964346879,
#             {"h3_cell": pl.UInt64},
#             "km",
#             10.302930275179133,
#             id="uint64_km",
#         ),
#         pytest.param(
#             1608492358964346879,
#             {"h3_cell": pl.Int64},
#             "km",
#             10.302930275179133,
#             id="int64_km",
#         ),
#         pytest.param("fffffffffffffff", None, "km", None, id="invalid_edge"),
#     ],
# )
# def test_edge_length(
#     h3_cell: Union[str, int],
#     schema: Union[Dict[str, pl.DataType], None],
#     unit: str,
#     expected_length: float | None,
# ):
#     df = pl.DataFrame({"h3_cell": [h3_cell]}, schema=schema).with_columns(
#         length=polars_h3.edge_length(pl.col("h3_cell"), unit)
#     )
#     if expected_length is None:
#         assert df["length"][0] is None
#     else:
#         assert pytest.approx(df["length"][0], rel=1e-9) == expected_length


# @pytest.mark.parametrize(
#     "resolution, expected_count",
#     [
#         pytest.param(0, 122, id="res0"),
#         pytest.param(5, 2016842, id="res5"),
#         # pytest.param(-1, None, id="invalid_res"),
#     ],
# )
# def test_get_num_cells(resolution: int, expected_count: int | None):
#     df = pl.DataFrame({"resolution": [resolution]}).with_columns(
#         count=polars_h3.get_num_cells("resolution")
#     )
#     assert df["count"].to_list()[0] == expected_count


# def test_get_res0_cells():
#     df = pl.DataFrame({"dummy": [1]}).with_columns(
#         [
#             polars_h3.get_res0_cells().alias("cells_int"),
#         ]
#     )

#     assert len(df["cells_int"][0]) == 122
#     assert len(df["cells_str"][0]) == 122


# @pytest.mark.parametrize(
#     "resolution, expected_valid",
#     [
#         pytest.param(-1, False, id="negative_res"),
#         pytest.param(16, False, id="too_high_res"),
#         pytest.param(0, True, id="valid_res_0"),
#         pytest.param(5, True, id="valid_res_5"),
#     ],
# )
# def test_get_pentagons(resolution: int, expected_valid: bool):
#     df = pl.DataFrame({"resolution": [resolution]}).with_columns(
#         [
#             polars_h3.get_pentagons("resolution").alias("pent_int"),
#             polars_h3.get_pentagons_string("resolution").alias("pent_str"),
#         ]
#     )

#     if expected_valid:
#         assert len(df["pent_int"][0]) == 12  # Always 12 pentagons per resolution
#         assert len(df["pent_str"][0]) == 12
#     else:
#         assert df["pent_int"][0] is None
#         assert df["pent_str"][0] is None
