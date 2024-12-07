import polars as pl
import pytest

import polars_h3


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input_lat1": 40.7128,
                "input_lng1": -74.0060,
                "input_lat2": 40.7128,
                "input_lng2": -74.0060,
                "unit": "km",
                "output": 0,
            },
            id="same_point_km",
        ),
        pytest.param(
            {
                "input_lat1": 40.7128,
                "input_lng1": -74.0060,
                "input_lat2": 42.3601,
                "input_lng2": -71.0589,
                "unit": "km",
                "output": 306.108,
            },
            id="diff_points_km",
        ),
        pytest.param(
            {
                "input_lat1": 40.7128,
                "input_lng1": -74.0060,
                "input_lat2": 42.3601,
                "input_lng2": -71.0589,
                "unit": "m",
                "output": 306108,
            },
            id="diff_points_m",
        ),
        pytest.param(
            {
                "input_lat1": 40.7128,
                "input_lng1": -74.0060,
                "input_lat2": 34.0522,
                "input_lng2": -118.2437,
                "unit": "km",
                "output": 3936.155,
            },
            id="large_distance_km",
        ),
        pytest.param(
            {
                "input_lat1": 40.7128,
                "input_lng1": -74.0060,
                "input_lat2": 34.0522,
                "input_lng2": -118.2437,
                "unit": "m",
                "output": 3936155,
            },
            id="large_distance_m",
        ),
    ],
)
def test_great_circle_distance(test_params):
    df = pl.DataFrame(
        {
            "lat1": [test_params["input_lat1"]],
            "lng1": [test_params["input_lng1"]],
            "lat2": [test_params["input_lat2"]],
            "lng2": [test_params["input_lng2"]],
        }
    ).with_columns(
        distance=polars_h3.great_circle_distance(
            "lat1", "lng1", "lat2", "lng2", test_params["unit"]
        )
    )
    if test_params["output"] is None:
        assert df["distance"][0] is None
    else:
        assert pytest.approx(df["distance"][0], rel=1e-3) == test_params["output"]


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": 0,
                "unit": "km^2",
                "output": 4357449.416078383,
            },
            id="res0_km2",
        ),
        pytest.param(
            {
                "input": 1,
                "unit": "km^2",
                "output": 609788.4417941332,
            },
            id="res1_km2",
        ),
        pytest.param(
            {
                "input": 9,
                "unit": "m^2",
                "output": 105332.51342720671,
            },
            id="res0_m2",
        ),
        pytest.param(
            {
                "input": 10,
                "unit": "m^2",
                "output": 15047.50190766435,
            },
            id="res1_m2",
        ),
        # pytest.param(
        #     {
        #         "input": -1,
        #         "unit": "km^2",
        #         "output": None,
        #     },
        #     id="invalid_res",
        # ),
    ],
)
def test_average_hexagon_area(test_params):
    df = pl.DataFrame({"resolution": [test_params["input"]]}).with_columns(
        polars_h3.average_hexagon_area(pl.col("resolution"), test_params["unit"]).alias(
            "area"
        )
    )
    if test_params["output"] is None:
        assert df["area"][0] is None
    else:
        assert pytest.approx(df["area"][0], rel=1e-2) == test_params["output"]


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": "8928308280fffff",
                "schema": None,
                "unit": "km^2",
                "output": 0.1093981886464832,
            },
            id="string_km2",
        ),
        pytest.param(
            {
                "input": "8928308280fffff",
                "schema": None,
                "unit": "m^2",
                "output": 109398.18864648319,
            },
            id="string_m2",
        ),
        pytest.param(
            {
                "input": 586265647244115967,
                "schema": {"h3_cell": pl.UInt64},
                "unit": "km^2",
                "output": 85321.69572540345,
            },
            id="uint64_km2",
        ),
        pytest.param(
            {
                "input": 586265647244115967,
                "schema": {"h3_cell": pl.Int64},
                "unit": "km^2",
                "output": 85321.69572540345,
            },
            id="int64_km2",
        ),
        pytest.param(
            {
                "input": "fffffffffffffff",
                "schema": None,
                "unit": "km^2",
                "output": None,
            },
            id="invalid_cell",
        ),
    ],
)
def test_hexagon_area(test_params):
    df = pl.DataFrame(
        {"h3_cell": [test_params["input"]]},
        schema=test_params["schema"],
    ).with_columns(area=polars_h3.cell_area(pl.col("h3_cell"), test_params["unit"]))
    if test_params["output"] is None:
        assert df["area"][0] is None
    else:
        assert pytest.approx(df["area"][0], rel=1e-9) == test_params["output"]


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": 0,
                "unit": "km",
                "output": 1107.712591,
            },
            id="res0_km",
        ),
        pytest.param(
            {
                "input": 1,
                "unit": "km",
                "output": 418.6760055,
            },
            id="res1_km",
        ),
        pytest.param(
            {
                "input": 0,
                "unit": "m",
                "output": 1107712.591,
            },
            id="res0_m",
        ),
        pytest.param(
            {
                "input": 1,
                "unit": "m",
                "output": 418676.0,
            },
            id="res1_m",
        ),
        # pytest.param(
        #     {
        #         "input": -1,
        #         "unit": "km",
        #         "output": None,
        #     },
        #     id="invalid_res",
        # ),
    ],
)
def test_average_hexagon_edge_length(test_params):
    df = pl.DataFrame({"resolution": [test_params["input"]]}).with_columns(
        length=polars_h3.average_hexagon_edge_length(
            pl.col("resolution"), test_params["unit"]
        )
    )
    if test_params["output"] is None:
        assert df["length"][0] is None
    else:
        assert pytest.approx(df["length"][0], rel=1e-3) == test_params["output"]


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
