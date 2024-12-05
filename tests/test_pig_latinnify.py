import polars as pl
from h3_polars import pig_latinnify


def test_piglatinnify():
    df = pl.DataFrame(
        {
            "english": ["this", "is", "not", "pig", "latin"],
        }
    )
    result = df.with_columns(pig_latin=pig_latinnify("english"))

    expected_df = pl.DataFrame(
        {
            "english": ["this", "is", "not", "pig", "latin"],
            "pig_latin": ["histay", "siay", "otnay", "igpay", "atinlay"],
        }
    )

    assert result.equals(expected_df)
