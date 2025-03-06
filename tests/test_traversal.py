import polars as pl
import pytest

import polars_h3


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": 622054503267303423,
                "schema": None,
                "output_disk_radius_0": [622054503267303423],
                "output_disk_radius_1": [
                    622054502770606079,
                    622054502770835455,
                    622054502770900991,
                    622054503267205119,
                    622054503267237887,
                    622054503267270655,
                    622054503267303423,
                ],
            },
            id="int_no_schema",
        ),
        pytest.param(
            {
                "input": 622054503267303423,
                "schema": {"input": pl.UInt64},
                "output_disk_radius_0": [622054503267303423],
                "output_disk_radius_1": [
                    622054502770606079,
                    622054502770835455,
                    622054502770900991,
                    622054503267205119,
                    622054503267237887,
                    622054503267270655,
                    622054503267303423,
                ],
            },
            id="uint64_with_schema",
        ),
        pytest.param(
            {
                "input": "8a1fb46622dffff",
                "schema": None,
                "output_disk_radius_0": ["8a1fb46622dffff"],
                "output_disk_radius_1": [
                    "8a1fb464492ffff",
                    "8a1fb4644967fff",
                    "8a1fb4644977fff",
                    "8a1fb46622c7fff",
                    "8a1fb46622cffff",
                    "8a1fb46622d7fff",
                    "8a1fb46622dffff",
                ],
            },
            id="string_input",
        ),
    ],
)
def test_grid_disk(test_params):
    df = pl.DataFrame(
        {"input": [test_params["input"]]}, schema=test_params["schema"]
    ).with_columns(
        polars_h3.grid_disk("input", 0).list.sort().alias("disk_radius_0"),
        polars_h3.grid_disk("input", 1).list.sort().alias("disk_radius_1"),
        polars_h3.grid_disk("input", 2).list.sort().alias("disk_radius_2"),
    )

    assert df["disk_radius_0"].to_list()[0] == test_params["output_disk_radius_0"]
    assert df["disk_radius_1"].to_list()[0] == test_params["output_disk_radius_1"]

    assert len(df["disk_radius_2"].to_list()[0]) == 19


def test_grid_disk_raises_invalid_k():
    with pytest.raises(ValueError):
        pl.DataFrame({"h3_cell": ["8a1fb46622dffff"]}).with_columns(
            polars_h3.grid_disk("h3_cell", -1).alias("disk")
        )


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": "8a1fb46622dffff",
                "k": 0,
                "schema": None,
                "output": ["8a1fb46622dffff"],
            },
            id="string_k0",
        ),
        pytest.param(
            {
                "input": "8a1fb46622dffff",
                "k": 1,
                "schema": None,
                "output": [
                    "8a1fb464492ffff",
                    "8a1fb4644967fff",
                    "8a1fb4644977fff",
                    "8a1fb46622c7fff",
                    "8a1fb46622cffff",
                    "8a1fb46622d7fff",
                ],
            },
            id="string_k1",
        ),
        pytest.param(
            {
                "input": 622054503267303423,
                "k": 0,
                "schema": {"input": pl.UInt64},
                "output": [622054503267303423],
            },
            id="uint64_k1",
        ),
        pytest.param(
            {
                "input": 622054503267303423,
                "k": 1,
                "schema": {"input": pl.UInt64},
                "output": [
                    622054502770606079,
                    622054502770835455,
                    622054502770900991,
                    622054503267205119,
                    622054503267237887,
                    622054503267270655,
                ],
            },
            id="uint64_k2",
        ),
    ],
)
def test_grid_ring(test_params):
    df = pl.DataFrame(
        {"input": [test_params["input"]]}, schema=test_params["schema"]
    ).with_columns(
        polars_h3.grid_ring("input", test_params["k"]).list.sort().alias("ring")
    )

    assert df["ring"].to_list()[0] == sorted(test_params["output"])


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input_1": 605035864166236159,
                "input_2": 605035864166236159,
                "schema": {"input_1": pl.UInt64, "input_2": pl.UInt64},
                "output": [605035864166236159],
            },
            id="single_path",
        ),
        pytest.param(
            {
                "input_1": 605035864166236159,
                "input_2": 605034941150920703,
                "schema": {"input_1": pl.UInt64, "input_2": pl.UInt64},
                "output": [
                    605035864166236159,
                    605035861750317055,
                    605035861347663871,
                    605035862018752511,
                    605034941419356159,
                    605034941150920703,
                ],
            },
            id="valid_path_uint64",
        ),
        pytest.param(
            {
                "input_1": 605035864166236159,
                "input_2": 605034941150920703,
                "schema": {"input_1": pl.Int64, "input_2": pl.Int64},
                "output": [
                    605035864166236159,
                    605035861750317055,
                    605035861347663871,
                    605035862018752511,
                    605034941419356159,
                    605034941150920703,
                ],
            },
            id="valid_path_int64",
        ),
        pytest.param(
            {
                "input_1": "86584e9afffffff",
                "input_2": "8658412c7ffffff",
                "schema": None,
                "output": [
                    "86584e9afffffff",
                    "86584e91fffffff",
                    "86584e907ffffff",
                    "86584e92fffffff",
                    "8658412d7ffffff",
                    "8658412c7ffffff",
                ],
            },
            id="valid_path_string",
        ),
        pytest.param(
            {
                "input_1": 605035864166236159,
                "input_2": 0,
                "schema": {"input_1": pl.UInt64, "input_2": pl.UInt64},
                "output": None,
            },
            id="invalid_path_uint64_to_zero",
        ),
        pytest.param(
            {
                "input_1": 605035864166236159,
                "input_2": 0,
                "schema": {"input_1": pl.Int64, "input_2": pl.Int64},
                "output": None,
            },
            id="invalid_path_int64_to_zero",
        ),
        pytest.param(
            {
                "input_1": "86584e9afffffff",
                "input_2": "0",
                "schema": None,
                "output": None,
            },
            id="invalid_path_string_to_zero",
        ),
        pytest.param(
            {
                "input_1": "0",
                "input_2": "86584e9afffffff",
                "schema": None,
                "output": None,
            },
            id="invalid_path_zero_to_string",
        ),
    ],
)
def test_grid_path_cells(test_params):
    df = pl.DataFrame(
        {
            "input_1": [test_params["input_1"]],
            "input_2": [test_params["input_2"]],
        },
        schema=test_params["schema"],
    ).with_columns(
        polars_h3.grid_path_cells("input_1", "input_2").list.sort().alias("path")
    )
    sorted_output = sorted(test_params["output"]) if test_params["output"] else None
    assert df["path"].to_list()[0] == sorted_output


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input_1": "86584e9afffffff",
                "input_2": "8658412c7ffffff",
                "schema": None,
                "output": 5,
            },
            id="string_valid_distance",
        ),
        pytest.param(
            {
                "input_1": 605035864166236159,
                "input_2": 605034941150920703,
                "schema": {"input_1": pl.UInt64, "input_2": pl.UInt64},
                "output": 5,
            },
            id="uint64_valid_distance",
        ),
        pytest.param(
            {
                "input_1": 605035864166236159,
                "input_2": 605034941150920703,
                "schema": {"input_1": pl.Int64, "input_2": pl.Int64},
                "output": 5,
            },
            id="int64_valid_distance",
        ),
        pytest.param(
            {
                "input_1": 605035864166236159,
                "input_2": 0,
                "schema": {"input_1": pl.Int64, "input_2": pl.Int64},
                "output": None,
            },
            id="int64_to_zero",
        ),
        pytest.param(
            {
                "input_1": 605035864166236159,
                "input_2": 0,
                "schema": {"input_1": pl.UInt64, "input_2": pl.UInt64},
                "output": None,
            },
            id="uint64_to_zero",
        ),
        pytest.param(
            {
                "input_1": "86584e9afffffff",
                "input_2": "0",
                "schema": None,
                "output": None,
            },
            id="string_to_zero",
        ),
        pytest.param(
            {
                "input_1": "872a10006ffffff",
                "input_2": "862a108dfffffff",
                "schema": None,
                "output": None,
            },
            id="different_resolutions",
        ),
    ],
)
def test_grid_distance(test_params):
    df = pl.DataFrame(
        {
            "input_1": [test_params["input_1"]],
            "input_2": [test_params["input_2"]],
        },
        schema=test_params["schema"],
    ).with_columns(polars_h3.grid_distance("input_1", "input_2").alias("distance"))

    assert df["distance"].to_list()[0] == test_params["output"]


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "origin": 605034941285138431,
                "dest": 605034941285138431,
                "schema": {"origin": pl.UInt64, "dest": pl.UInt64},
                "output": [-123, -177],
            },
            id="uint64_same_cell",
        ),
        pytest.param(
            {
                "origin": 605034941285138431,
                "dest": 605034941285138431,
                "schema": {"origin": pl.Int64, "dest": pl.Int64},
                "output": [-123, -177],
            },
            id="int64_same_cell",
        ),
        pytest.param(
            {
                "origin": "8658412cfffffff",
                "dest": "8658412cfffffff",
                "schema": None,
                "output": [-123, -177],
            },
            id="string_same_cell",
        ),
        pytest.param(
            {
                "origin": 605034941285138431,
                "dest": 0,
                "schema": {"origin": pl.UInt64, "dest": pl.UInt64},
                "output": None,
            },
            id="uint64_to_zero",
        ),
        pytest.param(
            {
                "origin": 605034941285138431,
                "dest": 0,
                "schema": {"origin": pl.Int64, "dest": pl.Int64},
                "output": None,
            },
            id="int64_to_zero",
        ),
        pytest.param(
            {
                "origin": "8658412cfffffff",
                "dest": "0",
                "schema": None,
                "output": None,
            },
            id="string_to_zero",
        ),
        pytest.param(
            {
                "origin": "8658412cfffffff",
                "dest": "abc",
                "schema": None,
                "output": None,
            },
            id="string_to_invalid",
        ),
    ],
)
def test_cell_to_local_ij(test_params):
    df = pl.DataFrame(
        {
            "origin": [test_params["origin"]],
            "dest": [test_params["dest"]],
        },
        schema=test_params["schema"],
    ).with_columns(coords=polars_h3.cell_to_local_ij("origin", "dest"))

    assert df["coords"].to_list()[0] == test_params["output"]


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": 605034941285138431,
                "i": -123,
                "j": -177,
                "schema": {"origin": pl.UInt64},
                "output": 605034941285138431,
            },
            id="uint64_valid",
        ),
        pytest.param(
            {
                "input": 605034941285138431,
                "i": -123,
                "j": -177,
                "schema": {"origin": pl.Int64},
                "output": 605034941285138431,
            },
            id="int64_valid",
        ),
        pytest.param(
            {
                "input": "8658412cfffffff",
                "i": -123,
                "j": -177,
                "schema": None,
                "output": 605034941285138431,
            },
            id="string_valid",
        ),
        pytest.param(
            {
                "input": 605034941285138431,
                "i": -1230000,
                "j": -177,
                "schema": {"origin": pl.UInt64},
                "output": None,
            },
            id="uint64_invalid_coords",
        ),
        pytest.param(
            {
                "input": 605034941285138431,
                "i": -1230000,
                "j": -177,
                "schema": {"origin": pl.Int64},
                "output": None,
            },
            id="int64_invalid_coords",
        ),
        pytest.param(
            {
                "input": "8658412cfffffff",
                "i": -1230000,
                "j": -177,
                "schema": None,
                "output": None,
            },
            id="string_invalid_coords",
        ),
    ],
)
def test_local_ij_to_cell(test_params):
    df = pl.DataFrame(
        {"origin": [test_params["input"]]},
        schema=test_params["schema"],
    ).with_columns(
        cell=polars_h3.local_ij_to_cell("origin", test_params["i"], test_params["j"])
    )

    assert df["cell"].to_list()[0] == test_params["output"]


def test_grid_ring_and_disk_with_column_k():
    df = pl.DataFrame(
        {
            "cell": [622054503267303423, 622054503267303423, 622054503267303423],
            "k": [0, 1, 2],
        },
        schema={"cell": pl.UInt64, "k": pl.UInt32},
    )

    result = df.with_columns(
        polars_h3.grid_ring("cell", "k").list.sort().alias("ring"),
        polars_h3.grid_disk("cell", "k").list.sort().alias("disk"),
    )

    # Expected results for grid_ring
    assert result["ring"].to_list()[0] == [622054503267303423]  # k=0: just the origin
    assert result["ring"].to_list()[1] == sorted(
        [
            622054502770606079,
            622054502770835455,
            622054502770900991,
            622054503267205119,
            622054503267237887,
            622054503267270655,
        ]
    )  # k=1: ring of neighbors
    assert len(result["ring"].to_list()[2]) == 12

    # Expected results for grid_disk
    assert result["disk"].to_list()[0] == [622054503267303423]  # k=0: just the origin
    assert result["disk"].to_list()[1] == sorted(
        [
            622054502770606079,
            622054502770835455,
            622054502770900991,
            622054503267205119,
            622054503267237887,
            622054503267270655,
            622054503267303423,  # includes origin
        ]
    )  # k=1: disk including origin
    assert len(result["disk"].to_list()[2]) == 19


def test_grid_ring_k_supplied_as_int():
    df = pl.DataFrame(
        {
            "cell": [622054503267303423, 622054503267303423, 622054503267303423],
        },
        schema={"cell": pl.UInt64},
    )

    df.with_columns(
        polars_h3.grid_ring("cell", 1).list.sort().alias("ring"),
        polars_h3.grid_disk("cell", 1).list.sort().alias("disk"),
    )
