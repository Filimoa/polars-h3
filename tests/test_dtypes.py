import polars as pl
import pytest

import polars_h3 as plh3


def test_full_null_latlng():
    df = pl.DataFrame({"lat": [None] * 10000, "lng": [None] * 10000})
    with pytest.raises(pl.exceptions.ComputeError) as exc_info:
        df.with_columns(plh3.latlng_to_cell("lat", "lng", 9, return_dtype=pl.UInt64))
    # Check that the error message does not contain "panick"
    assert "panic" not in str(exc_info.value).lower()


def test_single_null_latlng():
    df = pl.DataFrame(
        {
            "lat": [40.7128] * 99 + [None],
            "lng": [-74.006] * 99 + [None],
        },
        schema={"lat": pl.Float64, "lng": pl.Float64},
    ).with_columns(h3_cell=plh3.latlng_to_cell("lat", "lng", 9, return_dtype=pl.UInt64))
    assert df["h3_cell"].is_null().sum() == 1


def test_float32_latlng():
    df = pl.DataFrame(
        {
            "lat": [40.7128] * 10,
            "lng": [-74.006] * 10,
        },
        schema={"lat": pl.Float32, "lng": pl.Float32},
    )

    df.with_columns(plh3.latlng_to_cell("lat", "lng", 9, return_dtype=pl.UInt64))
