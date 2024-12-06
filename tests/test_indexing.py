import pytest
import polars as pl
import polars_h3
from typing import Optional, Union, Dict, List


def test_latlng_to_cell_valid():
    df = pl.DataFrame({"lat": [0.0], "lng": [0.0]}).with_columns(
        h3_cell=polars_h3.latlng_to_cell("lat", "lng", 1)
    )
    assert df["h3_cell"][0] == 583031433791012863


def test_latlng_to_cell_string_valid():
    df = pl.DataFrame(
        {"lat": [37.7752702151959], "lng": [-122.418307270836]}
    ).with_columns(
        h3_cell=polars_h3.latlng_to_cell_string("lat", "lng", 9),
    )
    assert df["h3_cell"][0] == "8928308280fffff"


@pytest.mark.parametrize(
    "resolution",
    [
        pytest.param(-1, id="negative_resolution"),
        pytest.param(30, id="too_high_resolution"),
    ],
)
def test_latlng_to_cell_invalid_resolution(resolution: int):
    df = pl.DataFrame({"lat": [0.0], "lng": [0.0]})

    with pytest.raises(ValueError):
        df.with_columns(h3_cell=polars_h3.latlng_to_cell("lat", "lng", resolution))

    with pytest.raises(ValueError):
        df.with_columns(
            h3_cell=polars_h3.latlng_to_cell_string("lat", "lng", resolution)
        )


@pytest.mark.parametrize(
    "lat, lng",
    [
        pytest.param(37.7752702151959, None, id="null_longitude"),
        pytest.param(None, -122.418307270836, id="null_latitude"),
        pytest.param(None, None, id="both_null"),
    ],
)
def test_latlng_to_cell_null_inputs(lat: Optional[float], lng: Optional[float]):
    df = pl.DataFrame({"lat": [lat], "lng": [lng]})

    with pytest.raises(pl.exceptions.ComputeError):
        df.with_columns(h3_cell=polars_h3.latlng_to_cell("lat", "lng", 9))

    with pytest.raises(pl.exceptions.ComputeError):
        df.with_columns(h3_cell=polars_h3.latlng_to_cell_string("lat", "lng", 9))


@pytest.mark.parametrize(
    "h3_cell, schema",
    [
        pytest.param(
            [599686042433355775], {"int_h3_cell": pl.UInt64}, id="uint64_input"
        ),
        pytest.param([599686042433355775], {"int_h3_cell": pl.Int64}, id="int64_input"),
        pytest.param(["85283473fffffff"], None, id="string_input"),
    ],
)
def test_cell_to_latlng(
    h3_cell: List[Union[int, str]], schema: Union[Dict[str, pl.DataType], None]
):
    df = pl.DataFrame({"int_h3_cell": h3_cell}, schema=schema).with_columns(
        lat=polars_h3.cell_to_lat("int_h3_cell"),
        lng=polars_h3.cell_to_lng("int_h3_cell"),
    )
    assert pytest.approx(df["lat"][0], 0.00001) == 37.345793375368
    assert pytest.approx(df["lng"][0], 0.00001) == -121.976375972551
