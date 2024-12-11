import polars as pl
import pytest

import polars_h3


@pytest.mark.parametrize(
    "input_lat,input_lng,resolution,return_dtype,expected",
    [
        (0.0, 0.0, 1, pl.UInt64, 583031433791012863),
        (37.7752702151959, -122.418307270836, 9, pl.Utf8, "8928308280fffff"),
    ],
    ids=["cell_int", "cell_string"],
)
def test_latlng_to_cell_valid(input_lat, input_lng, resolution, return_dtype, expected):
    df = pl.DataFrame({"lat": [input_lat], "lng": [input_lng]}).with_columns(
        h3_cell=polars_h3.latlng_to_cell(
            "lat", "lng", resolution, return_dtype=return_dtype
        )
    )
    assert df["h3_cell"][0] == expected


@pytest.mark.parametrize(
    "input_lat,input_lng,resolution",
    [
        (0.0, 0.0, -1),
        (0.0, 0.0, 30),
    ],
    ids=["negative_resolution", "too_high_resolution"],
)
def test_latlng_to_cell_invalid_resolution(input_lat, input_lng, resolution):
    df = pl.DataFrame({"lat": [input_lat], "lng": [input_lng]})
    with pytest.raises(ValueError):
        df.with_columns(
            h3_cell=polars_h3.latlng_to_cell(
                "lat", "lng", resolution, return_dtype=pl.UInt64
            )
        )
    with pytest.raises(ValueError):
        df.with_columns(
            h3_cell=polars_h3.latlng_to_cell(
                "lat", "lng", resolution, return_dtype=pl.Utf8
            )
        )


def test_latlng_to_cell_missing_lat_lng():
    df = pl.DataFrame({"lat": [None], "lng": [None]})
    with pytest.raises(pl.exceptions.ComputeError):
        df.with_columns(
            h3_cell=polars_h3.latlng_to_cell("lat", "lng", 9, return_dtype=pl.UInt64)
        )


@pytest.mark.parametrize(
    "input_lat,input_lng",
    [
        (37.7752702151959, None),
        (None, -122.418307270836),
        (None, None),
    ],
    ids=["null_longitude", "null_latitude", "both_null"],
)
def test_latlng_to_cell_null_inputs(input_lat, input_lng):
    df = pl.DataFrame({"lat": [input_lat], "lng": [input_lng]})
    with pytest.raises(pl.exceptions.ComputeError):
        df.with_columns(
            h3_cell=polars_h3.latlng_to_cell("lat", "lng", 9, return_dtype=pl.UInt64)
        )
    with pytest.raises(pl.exceptions.ComputeError):
        df.with_columns(
            h3_cell=polars_h3.latlng_to_cell("lat", "lng", 9, return_dtype=pl.Utf8)
        )


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": 599686042433355775,
                "output_lat": 37.345793375368,
                "output_lng": -121.976375972551,
                "schema": {"input": pl.UInt64},
            },
            id="uint64_input",
        ),
        pytest.param(
            {
                "input": 599686042433355775,
                "output_lat": 37.345793375368,
                "output_lng": -121.976375972551,
                "schema": {"input": pl.Int64},
            },
            id="int64_input",
        ),
        pytest.param(
            {
                "input": "85283473fffffff",
                "output_lat": 37.345793375368,
                "output_lng": -121.976375972551,
                "schema": None,
            },
            id="string_input",
        ),
    ],
)
def test_cell_to_latlng(test_params):
    df = pl.DataFrame(
        {"input": [test_params["input"]]}, schema=test_params["schema"]
    ).with_columns(
        lat=polars_h3.cell_to_lat("input"),
        lng=polars_h3.cell_to_lng("input"),
    )
    assert pytest.approx(df["lat"][0], 0.00001) == test_params["output_lat"]
    assert pytest.approx(df["lng"][0], 0.00001) == test_params["output_lng"]


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": "8a1fb464492ffff",
                "output_boundary": [
                    (48.853925897310056, 2.3725526996968154),
                    (48.853762357995556, 2.371650760662443),
                    (48.85311886121302, 2.3714610612212152),
                    (48.85263890985581, 2.3721732876265516),
                    (48.85280245093953, 2.3730752066146477),
                    (48.85344594161119, 2.3732649192433906),
                ],
            },
            id="case_string_paris",
        ),
        pytest.param(
            {
                "input": "812bbffffffffff",
                "output_boundary": [
                    (50.99021068384578, -76.05772874399094),
                    (48.295316381881364, -81.91962699890831),
                    (43.86011974432308, -80.98225290216081),
                    (42.02956371225369, -75.33345172379178),
                    (44.27784933847793, -69.95506755076666),
                    (48.757431677563375, -69.71947899952944),
                ],
            },
            id="case_string_large",
        ),
        pytest.param(
            {
                "input": 581734010070237183,
                "output_boundary": [
                    (50.99021068384578, -76.05772874399094),
                    (48.295316381881364, -81.91962699890831),
                    (43.86011974432308, -80.98225290216081),
                    (42.02956371225369, -75.33345172379178),
                    (44.27784933847793, -69.95506755076666),
                    (48.757431677563375, -69.71947899952944),
                ],
            },
            id="case_int_large",
        ),
    ],
)
def test_cell_to_boundary_known(test_params):
    df = pl.DataFrame({"cell": [test_params["input"]]}).with_columns(
        boundary=polars_h3.cell_to_boundary("cell")
    )
    boundary = df["boundary"][0]
    for i, (exp_lat, exp_lng) in enumerate(test_params["output_boundary"]):
        lat, lng = boundary[i]
        assert pytest.approx(lat, abs=1e-7) == exp_lat
        assert pytest.approx(lng, abs=1e-7) == exp_lng
