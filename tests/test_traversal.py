import pytest
import polars as pl
import polars_h3
from typing import Union, List, Dict


@pytest.mark.parametrize(
    "h3_cell, schema",
    [
        (
            [622054503267303423],
            None,
        ),
        (
            [622054503267303423],
            {"h3_cell": pl.UInt64},
        ),
        (
            ["8a1fb46622dffff"],
            None,
        ),
    ],
)
def test_grid_disk(
    h3_cell: List[Union[int, str]], schema: Union[Dict[str, pl.DataType], None]
):
    df = pl.DataFrame({"h3_cell": h3_cell}, schema=schema).with_columns(
        polars_h3.grid_disk("h3_cell", 0).list.sort().alias("disk_radius_0"),
        polars_h3.grid_disk("h3_cell", 1).list.sort().alias("disk_radius_1"),
        polars_h3.grid_disk("h3_cell", 2).list.sort().alias("disk_radius_2"),
    )
    assert df["disk_radius_0"].to_list()[0] == [622054503267303423]
    assert df["disk_radius_1"].to_list()[0] == [
        622054502770606079,
        622054502770835455,
        622054502770900991,
        622054503267205119,
        622054503267237887,
        622054503267270655,
        622054503267303423,
    ]

    assert df["disk_radius_2"].to_list()[0] == [
        622054502770442239,
        622054502770475007,
        622054502770573311,
        622054502770606079,
        622054502770704383,
        622054502770769919,
        622054502770835455,
        622054502770868223,
        622054502770900991,
        622054503266975743,
        622054503267205119,
        622054503267237887,
        622054503267270655,
        622054503267303423,
        622054503267336191,
        622054503267368959,
        622054503267401727,
        622054503286931455,
        622054503287062527,
    ]


def test_grid_disk_raises_invalid_k():
    with pytest.raises(ValueError):
        pl.DataFrame({"h3_cell": ["8a1fb46622dffff"]}).with_columns(
            polars_h3.grid_disk("h3_cell", -1).alias("disk")
        )


@pytest.mark.parametrize(
    "h3_cell_1, h3_cell_2, schema, expected_path",
    [
        pytest.param(
            [605035864166236159],
            [605035864166236159],
            {"h3_cell_1": pl.UInt64, "h3_cell_2": pl.UInt64},
            [
                605035864166236159,
            ],
            id="single_path",
        ),
        pytest.param(
            [605035864166236159],
            [605034941150920703],
            {"h3_cell_1": pl.UInt64, "h3_cell_2": pl.UInt64},
            [
                605035864166236159,
                605035861750317055,
                605035861347663871,
                605035862018752511,
                605034941419356159,
                605034941150920703,
            ],
            id="valid_path_uint64",
        ),
        pytest.param(
            [605035864166236159],
            [605034941150920703],
            {"h3_cell_1": pl.Int64, "h3_cell_2": pl.Int64},
            [
                605035864166236159,
                605035861750317055,
                605035861347663871,
                605035862018752511,
                605034941419356159,
                605034941150920703,
            ],
            id="valid_path_int64",
        ),
        pytest.param(
            ["86584e9afffffff"],
            ["8658412c7ffffff"],
            None,
            [
                605035864166236159,
                605035861750317055,
                605035861347663871,
                605035862018752511,
                605034941419356159,
                605034941150920703,
            ],
            id="valid_path_string",
        ),
        pytest.param(
            [605035864166236159],
            [0],
            {"h3_cell_1": pl.UInt64, "h3_cell_2": pl.UInt64},
            None,
            id="invalid_path_uint64_to_zero",
        ),
        pytest.param(
            [605035864166236159],
            [0],
            {"h3_cell_1": pl.Int64, "h3_cell_2": pl.Int64},
            None,
            id="invalid_path_int64_to_zero",
        ),
        pytest.param(
            ["86584e9afffffff"],
            ["0"],
            None,
            None,
            id="invalid_path_string_to_zero",
        ),
        pytest.param(
            ["0"],
            ["86584e9afffffff"],
            None,
            None,
            id="invalid_path_zero_to_string",
        ),
    ],
)
def test_grid_path_cells(
    h3_cell_1: List[Union[int, str]],
    h3_cell_2: List[Union[int, str]],
    schema: Union[Dict[str, pl.DataType], None],
    expected_path: List[Union[int, str, None]],
):
    df = pl.DataFrame(
        {
            "h3_cell_1": h3_cell_1,
            "h3_cell_2": h3_cell_2,
        },
        schema=schema,
    ).with_columns(
        polars_h3.grid_path_cells("h3_cell_1", "h3_cell_2").list.sort().alias("path")
    )
    sorted_expected_path = sorted(expected_path) if expected_path else None
    assert df["path"].to_list()[0] == sorted_expected_path


def test_grid_distance():
    # string
    df = pl.DataFrame(
        {"h3_cell_1": ["86584e9afffffff"], "h3_cell_2": ["8658412c7ffffff"]}
    ).with_columns(polars_h3.grid_distance("h3_cell_1", "h3_cell_2").alias("distance"))
    assert df["distance"].to_list()[0] == 5

    # unsigned
    df = pl.DataFrame(
        {
            "h3_cell_1": [605035864166236159],
            "h3_cell_2": [605034941150920703],
        },
        schema={"h3_cell_1": pl.UInt64, "h3_cell_2": pl.UInt64},
    ).with_columns(polars_h3.grid_distance("h3_cell_1", "h3_cell_2").alias("distance"))
    assert df["distance"].to_list()[0] == 5

    # signed
    df = pl.DataFrame(
        {
            "h3_cell_1": [605035864166236159],
            "h3_cell_2": [605034941150920703],
        },
        schema={"h3_cell_1": pl.Int64, "h3_cell_2": pl.Int64},
    ).with_columns(polars_h3.grid_distance("h3_cell_1", "h3_cell_2").alias("distance"))
    assert df["distance"].to_list()[0] == 5

    # signed to 0
    df = pl.DataFrame(
        {
            "h3_cell_1": [605035864166236159],
            "h3_cell_2": [0],
        },
        schema={"h3_cell_1": pl.Int64, "h3_cell_2": pl.Int64},
    ).with_columns(polars_h3.grid_distance("h3_cell_1", "h3_cell_2").alias("distance"))
    assert df["distance"].to_list()[0] is None

    # unsigned to 0
    df = pl.DataFrame(
        {
            "h3_cell_1": [605035864166236159],
            "h3_cell_2": [0],
        },
        schema={"h3_cell_1": pl.UInt64, "h3_cell_2": pl.UInt64},
    ).with_columns(polars_h3.grid_distance("h3_cell_1", "h3_cell_2").alias("distance"))
    assert df["distance"].to_list()[0] is None

    # utf8
    df = pl.DataFrame(
        {
            "h3_cell_1": ["86584e9afffffff"],
            "h3_cell_2": ["0"],
        },
    ).with_columns(polars_h3.grid_distance("h3_cell_1", "h3_cell_2").alias("distance"))
    assert df["distance"].to_list()[0] is None


@pytest.mark.parametrize(
    "origin, dest, schema, expected_coords",
    [
        pytest.param(
            [605034941285138431],
            [605034941285138431],
            {"origin": pl.UInt64, "dest": pl.UInt64},
            [-123, -177],
            id="uint64_same_cell",
        ),
        pytest.param(
            [605034941285138431],
            [605034941285138431],
            {"origin": pl.Int64, "dest": pl.Int64},
            [-123, -177],
            id="int64_same_cell",
        ),
        pytest.param(
            ["8658412cfffffff"],
            ["8658412cfffffff"],
            None,
            [-123, -177],
            id="string_same_cell",
        ),
        pytest.param(
            [605034941285138431],
            [0],
            {"origin": pl.UInt64, "dest": pl.UInt64},
            None,
            id="uint64_to_zero",
        ),
        pytest.param(
            [605034941285138431],
            [0],
            {"origin": pl.Int64, "dest": pl.Int64},
            None,
            id="int64_to_zero",
        ),
        pytest.param(["8658412cfffffff"], ["0"], None, None, id="string_to_zero"),
        pytest.param(["8658412cfffffff"], ["abc"], None, None, id="string_to_invalid"),
    ],
)
def test_cell_to_local_ij(
    origin: List[Union[int, str]],
    dest: List[Union[int, str]],
    schema: Union[Dict[str, pl.DataType], None],
    expected_coords: Union[List[int], None],
):
    df = pl.DataFrame(
        {"origin": origin, "dest": dest},
        schema=schema,
    ).with_columns(coords=polars_h3.cell_to_local_ij("origin", "dest"))
    assert df["coords"].to_list()[0] == expected_coords


@pytest.mark.parametrize(
    "origin, i, j, schema, expected_cell",
    [
        pytest.param(
            [605034941285138431],
            -123,
            -177,
            {"origin": pl.UInt64},
            605034941285138431,
            id="uint64_valid",
        ),
        pytest.param(
            [605034941285138431],
            -123,
            -177,
            {"origin": pl.Int64},
            605034941285138431,
            id="int64_valid",
        ),
        pytest.param(
            ["8658412cfffffff"], -123, -177, None, 605034941285138431, id="string_valid"
        ),
        pytest.param(
            [605034941285138431],
            -1230000,
            -177,
            {"origin": pl.UInt64},
            None,
            id="uint64_invalid_coords",
        ),
        pytest.param(
            [605034941285138431],
            -1230000,
            -177,
            {"origin": pl.Int64},
            None,
            id="int64_invalid_coords",
        ),
        pytest.param(
            ["8658412cfffffff"], -1230000, -177, None, None, id="string_invalid_coords"
        ),
    ],
)
def test_local_ij_to_cell(
    origin: List[Union[int, str]],
    i: int,
    j: int,
    schema: Union[Dict[str, pl.DataType], None],
    expected_cell: Union[int, str, None],
):
    df = pl.DataFrame({"origin": origin}, schema=schema).with_columns(
        cell=polars_h3.local_ij_to_cell("origin", i, j)
    )
    assert df["cell"].to_list()[0] == expected_cell
