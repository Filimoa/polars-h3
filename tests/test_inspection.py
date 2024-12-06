import pytest
import polars as pl
import polars_h3
from typing import List, Union, Dict


@pytest.mark.parametrize(
    "h3_input, schema, expected_resolution",
    [
        pytest.param(
            [586265647244115967], {"h3_cell": pl.UInt64}, 2, id="uint64_input"
        ),
        pytest.param([586265647244115967], {"h3_cell": pl.Int64}, 2, id="int64_input"),
        pytest.param(["822d57fffffffff"], None, 2, id="string_input"),
    ],
)
def test_get_resolution(
    h3_input: List[Union[int, str]],
    schema: Union[Dict[str, pl.DataType], None],
    expected_resolution: int,
):
    df = pl.DataFrame({"h3_cell": h3_input}, schema=schema).with_columns(
        resolution=polars_h3.get_resolution("h3_cell")
    )
    assert df["resolution"][0] == expected_resolution


@pytest.mark.parametrize(
    "h3_input, schema, expected_valid",
    [
        pytest.param(
            [586265647244115967], {"h3_cell": pl.UInt64}, True, id="valid_uint64"
        ),
        pytest.param(
            [586265647244115967], {"h3_cell": pl.Int64}, True, id="valid_int64"
        ),
        pytest.param(["85283473fffffff"], None, True, id="valid_string"),
        pytest.param([1234], {"h3_cell": pl.UInt64}, False, id="invalid_uint64"),
        pytest.param([1234], {"h3_cell": pl.Int64}, False, id="invalid_int64"),
        pytest.param(["1234"], None, False, id="invalid_string"),
    ],
)
def test_is_valid_cell(
    h3_input: List[Union[int, str]],
    schema: Union[Dict[str, pl.DataType], None],
    expected_valid: bool,
):
    df = pl.DataFrame({"h3_cell": h3_input}, schema=schema).with_columns(
        valid=polars_h3.is_valid_cell("h3_cell")
    )
    assert df["valid"][0] == expected_valid


@pytest.mark.parametrize(
    "h3_int_input, expected_str",
    [
        pytest.param([605035864166236159], "86584e9afffffff", id="number_1"),
        pytest.param([581698825698148351], "8129bffffffffff", id="number_2"),
        pytest.param([626682153101213695], "8b26c1912acbfff", id="number_3"),
        pytest.param([1], None, id="invalid_cell"),
    ],
)
def test_int_to_str_conversion(h3_int_input: List[int], expected_str: str):
    # Test UInt64
    df_uint = pl.DataFrame(
        {"h3_cell": h3_int_input}, schema={"h3_cell": pl.UInt64}
    ).with_columns(polars_h3.int_to_str("h3_cell").alias("h3_str"))
    assert df_uint["h3_str"].to_list()[0] == expected_str

    # Test Int64
    df_int = pl.DataFrame(
        {"h3_cell": h3_int_input}, schema={"h3_cell": pl.Int64}
    ).with_columns(h3_str=polars_h3.int_to_str("h3_cell"))
    assert df_int["h3_str"][0] == expected_str


@pytest.mark.parametrize(
    "h3_str_input, expected_int",
    [
        pytest.param(["86584e9afffffff"], 605035864166236159, id="number_1"),
        pytest.param(["8129bffffffffff"], 581698825698148351, id="number_2"),
        pytest.param(["8b26c1912acbfff"], 626682153101213695, id="number_3"),
        pytest.param(["sergey"], None, id="invalid_cell"),
    ],
)
def test_str_to_int_conversion(h3_str_input: List[str], expected_int: int):
    # Test UInt64
    df_uint = pl.DataFrame({"h3_cell": h3_str_input}).with_columns(
        polars_h3.str_to_int("h3_cell").alias("h3_int")
    )
    assert df_uint["h3_int"].to_list()[0] == expected_int

    # Test Int64
    df_int = pl.DataFrame({"h3_cell": h3_str_input}).with_columns(
        h3_int=polars_h3.str_to_int("h3_cell")
    )
    assert df_int["h3_int"][0] == expected_int


def test_is_pentagon():
    df = pl.DataFrame(
        {
            "h3_cell": [
                "821c07fffffffff",  # pentagon
                "85283473fffffff",  # not pentagon (regular hexagon)
            ]
        }
    ).with_columns(is_pent=polars_h3.is_pentagon("h3_cell"))
    assert df["is_pent"].to_list() == [True, False]

    df_int = pl.DataFrame(
        {
            "h3_cell": [585961082523222015, 599686042433355775],
        }
    ).with_columns(is_pent=polars_h3.is_pentagon("h3_cell"))
    assert df_int["is_pent"].to_list() == [True, False]


def test_is_res_class_III():
    # Resolution 1 (class III) and 2 (not class III) cells
    df = pl.DataFrame(
        {
            "h3_cell": [
                "81623ffffffffff",  # res 1 - should be class III
                "822d57fffffffff",  # res 2 - should not be class III
                "847c35fffffffff",
            ]
        }
    ).with_columns(is_class_3=polars_h3.is_res_class_III("h3_cell"))

    assert df["is_class_3"].to_list() == [True, False, False]

    # Test with integer representation too
    df_int = pl.DataFrame(
        {
            "h3_cell": [
                582692784209657855,  # res 1 cell - should be class III
                586265647244115967,  # res 2 cell - should not be class III
                596660292734156799,
            ]
        },
        schema={"h3_cell": pl.UInt64},
    ).with_columns(is_class_3=polars_h3.is_res_class_III("h3_cell"))

    assert df_int["is_class_3"].to_list() == [True, False, False]


def test_str_to_int_invalid():
    df = pl.DataFrame({"h3_str": [",,,,,"]}).with_columns(
        h3_int=polars_h3.str_to_int("h3_str")
    )
    assert df["h3_int"][0] is None


@pytest.mark.parametrize(
    "h3_input, schema, expected_faces",
    [
        pytest.param(
            [599686042433355775], {"h3_cell": pl.UInt64}, [7], id="single_face_uint64"
        ),
        pytest.param(
            [599686042433355775], {"h3_cell": pl.Int64}, [7], id="single_face_int64"
        ),
        pytest.param(["85283473fffffff"], None, [7], id="single_face_string"),
        pytest.param(
            [576988517884755967],
            {"h3_cell": pl.UInt64},
            [1, 6, 11, 7, 2],
            id="multiple_faces_uint64",
        ),
        pytest.param(
            [576988517884755967],
            {"h3_cell": pl.Int64},
            [1, 6, 11, 7, 2],
            id="multiple_faces_int64",
        ),
        pytest.param(
            ["801dfffffffffff"], None, [1, 6, 11, 7, 2], id="multiple_faces_string"
        ),
    ],
)
def test_get_icosahedron_faces(
    h3_input: List[Union[int, str]],
    schema: Union[Dict[str, pl.DataType], None],
    expected_faces: List[int],
):
    df = pl.DataFrame({"h3_cell": h3_input}, schema=schema).with_columns(
        faces=polars_h3.get_icosahedron_faces("h3_cell").list.sort()
    )
    assert df["faces"][0].to_list() == sorted(expected_faces)


@pytest.mark.parametrize(
    "h3_input, schema",
    [
        pytest.param(
            [18446744073709551615], {"h3_cell": pl.UInt64}, id="invalid_uint64"
        ),
        pytest.param([9223372036854775807], {"h3_cell": pl.Int64}, id="invalid_int64"),
        pytest.param(["7fffffffffffffff"], None, id="invalid_string"),
    ],
)
def test_get_icosahedron_faces_invalid(
    h3_input: List[Union[int, str]], schema: Union[Dict[str, pl.DataType], None]
):
    df = pl.DataFrame({"h3_cell": h3_input}, schema=schema).with_columns(
        faces=polars_h3.get_icosahedron_faces("h3_cell")
    )
    assert df["faces"][0] is None
