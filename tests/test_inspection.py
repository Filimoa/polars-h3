import polars as pl
import pytest

import polars_h3


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": 586265647244115967,
                "schema": {"h3_cell": pl.UInt64},
                "output": 2,
            },
            id="uint64_input",
        ),
        pytest.param(
            {
                "input": 586265647244115967,
                "schema": {"h3_cell": pl.Int64},
                "output": 2,
            },
            id="int64_input",
        ),
        pytest.param(
            {
                "input": "822d57fffffffff",
                "schema": None,
                "output": 2,
            },
            id="string_input",
        ),
    ],
)
def test_get_resolution(test_params):
    df = pl.DataFrame(
        {"h3_cell": [test_params["input"]]},
        schema=test_params["schema"],
    ).with_columns(resolution=polars_h3.get_resolution("h3_cell"))
    assert df["resolution"][0] == test_params["output"]


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": 586265647244115967,
                "schema": {"h3_cell": pl.UInt64},
                "output": True,
            },
            id="valid_uint64",
        ),
        pytest.param(
            {
                "input": 586265647244115967,
                "schema": {"h3_cell": pl.Int64},
                "output": True,
            },
            id="valid_int64",
        ),
        pytest.param(
            {
                "input": "85283473fffffff",
                "schema": None,
                "output": True,
            },
            id="valid_string",
        ),
        pytest.param(
            {
                "input": 1234,
                "schema": {"h3_cell": pl.UInt64},
                "output": False,
            },
            id="invalid_uint64",
        ),
        pytest.param(
            {
                "input": 1234,
                "schema": {"h3_cell": pl.Int64},
                "output": False,
            },
            id="invalid_int64",
        ),
        pytest.param(
            {
                "input": "1234",
                "schema": None,
                "output": False,
            },
            id="invalid_string",
        ),
    ],
)
def test_is_valid_cell(test_params):
    df = pl.DataFrame(
        {"h3_cell": [test_params["input"]]},
        schema=test_params["schema"],
    ).with_columns(valid=polars_h3.is_valid_cell("h3_cell"))
    assert df["valid"][0] == test_params["output"]


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": 605035864166236159,
                "output": "86584e9afffffff",
            },
            id="number_1",
        ),
        pytest.param(
            {
                "input": 581698825698148351,
                "output": "8129bffffffffff",
            },
            id="number_2",
        ),
        pytest.param(
            {
                "input": 626682153101213695,
                "output": "8b26c1912acbfff",
            },
            id="number_3",
        ),
        pytest.param(
            {
                "input": 1,
                "output": None,
            },
            id="invalid_cell",
        ),
    ],
)
def test_int_to_str_conversion(test_params):
    # Test UInt64
    df_uint = pl.DataFrame(
        {"h3_cell": [test_params["input"]]},
        schema={"h3_cell": pl.UInt64},
    ).with_columns(h3_str=polars_h3.int_to_str("h3_cell"))
    assert df_uint["h3_str"][0] == test_params["output"]

    # Test Int64
    df_int = pl.DataFrame(
        {"h3_cell": [test_params["input"]]},
        schema={"h3_cell": pl.Int64},
    ).with_columns(h3_str=polars_h3.int_to_str("h3_cell"))
    assert df_int["h3_str"][0] == test_params["output"]


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": "86584e9afffffff",
                "output": 605035864166236159,
            },
            id="number_1",
        ),
        pytest.param(
            {
                "input": "8129bffffffffff",
                "output": 581698825698148351,
            },
            id="number_2",
        ),
        pytest.param(
            {
                "input": "8b26c1912acbfff",
                "output": 626682153101213695,
            },
            id="number_3",
        ),
        pytest.param(
            {
                "input": "sergey",
                "output": None,
            },
            id="invalid_cell",
        ),
    ],
)
def test_str_to_int_conversion(test_params):
    # Test with no schema specified
    df_uint = pl.DataFrame({"h3_cell": [test_params["input"]]}).with_columns(
        h3_int=polars_h3.str_to_int("h3_cell")
    )
    assert df_uint["h3_int"][0] == test_params["output"]

    # Test with Int64 schema
    df_int = pl.DataFrame({"h3_cell": [test_params["input"]]}).with_columns(
        h3_int=polars_h3.str_to_int("h3_cell")
    )
    assert df_int["h3_int"][0] == test_params["output"]


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "inputs": ["821c07fffffffff", "85283473fffffff"],
                "outputs": [True, False],
                "schema": None,
            },
            id="string_input",
        ),
        pytest.param(
            {
                "inputs": [585961082523222015, 599686042433355775],
                "outputs": [True, False],
                "schema": {"h3_cell": pl.UInt64},
            },
            id="int_input",
        ),
    ],
)
def test_is_pentagon(test_params):
    df = pl.DataFrame(
        {"h3_cell": test_params["inputs"]},
        schema=test_params["schema"],
    ).with_columns(is_pent=polars_h3.is_pentagon("h3_cell"))
    assert df["is_pent"].to_list() == test_params["outputs"]


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "inputs": [
                    "81623ffffffffff",  # res 1 - should be class III
                    "822d57fffffffff",  # res 2 - should not be class III
                    "847c35fffffffff",
                ],
                "outputs": [True, False, False],
                "schema": None,
            },
            id="string_input",
        ),
        pytest.param(
            {
                "inputs": [
                    582692784209657855,  # res 1 cell - should be class III
                    586265647244115967,  # res 2 cell - should not be class III
                    596660292734156799,
                ],
                "outputs": [True, False, False],
                "schema": {"h3_cell": pl.UInt64},
            },
            id="int_input",
        ),
    ],
)
def test_is_res_class_III(test_params):
    df = pl.DataFrame(
        {"h3_cell": test_params["inputs"]},
        schema=test_params["schema"],
    ).with_columns(is_class_3=polars_h3.is_res_class_III("h3_cell"))
    assert df["is_class_3"].to_list() == test_params["outputs"]


def test_str_to_int_invalid():
    df = pl.DataFrame({"h3_str": [",,,,,"]}).with_columns(
        h3_int=polars_h3.str_to_int("h3_str")
    )
    assert df["h3_int"][0] is None


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": 599686042433355775,
                "schema": {"h3_cell": pl.UInt64},
                "output": [7],
            },
            id="single_face_uint64",
        ),
        pytest.param(
            {
                "input": 599686042433355775,
                "schema": {"h3_cell": pl.Int64},
                "output": [7],
            },
            id="single_face_int64",
        ),
        pytest.param(
            {
                "input": "85283473fffffff",
                "schema": None,
                "output": [7],
            },
            id="single_face_string",
        ),
        pytest.param(
            {
                "input": 576988517884755967,
                "schema": {"h3_cell": pl.UInt64},
                "output": [1, 6, 11, 7, 2],
            },
            id="multiple_faces_uint64",
        ),
        pytest.param(
            {
                "input": 576988517884755967,
                "schema": {"h3_cell": pl.Int64},
                "output": [1, 6, 11, 7, 2],
            },
            id="multiple_faces_int64",
        ),
        pytest.param(
            {
                "input": "801dfffffffffff",
                "schema": None,
                "output": [1, 6, 11, 7, 2],
            },
            id="multiple_faces_string",
        ),
    ],
)
def test_get_icosahedron_faces(test_params):
    df = pl.DataFrame(
        {"h3_cell": [test_params["input"]]},
        schema=test_params["schema"],
    ).with_columns(faces=polars_h3.get_icosahedron_faces("h3_cell").list.sort())
    assert df["faces"][0].to_list() == sorted(test_params["output"])


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": 18446744073709551615,
                "schema": {"h3_cell": pl.UInt64},
            },
            id="invalid_uint64",
        ),
        pytest.param(
            {
                "input": 9223372036854775807,
                "schema": {"h3_cell": pl.Int64},
            },
            id="invalid_int64",
        ),
        pytest.param(
            {
                "input": "7fffffffffffffff",
                "schema": None,
            },
            id="invalid_string",
        ),
    ],
)
def test_get_icosahedron_faces_invalid(test_params):
    df = pl.DataFrame(
        {"h3_cell": [test_params["input"]]},
        schema=test_params["schema"],
    ).with_columns(faces=polars_h3.get_icosahedron_faces("h3_cell"))
    assert df["faces"][0] is None
