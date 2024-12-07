import polars as pl
import pytest

import polars_h3


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": "2222597fffffffff",
                "schema": None,
                "output": False,
            },
            id="invalid_str_edge",
        ),
        pytest.param(
            {
                "input": 0,
                "schema": {"edge": pl.UInt64},
                "output": False,
            },
            id="invalid_int_edge",
        ),
        pytest.param(
            {
                "input": "115283473fffffff",
                "schema": None,
                "output": True,
            },
            id="valid_str_edge",
        ),
        pytest.param(
            {
                "input": 1248204388774707199,
                "schema": {"edge": pl.UInt64},
                "output": True,
            },
            id="valid_int_edge",
        ),
    ],
)
def test_is_valid_directed_edge(test_params):
    df = pl.DataFrame(
        {"edge": [test_params["input"]]},
        schema=test_params["schema"],
    ).with_columns(valid=polars_h3.is_valid_directed_edge("edge"))
    assert df["valid"][0] == test_params["output"]


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": 599686042433355775,
                "schema": {"h3_cell": pl.UInt64},
                "output_length": 6,
            },
            id="uint64_input",
        ),
        pytest.param(
            {
                "input": 599686042433355775,
                "schema": {"h3_cell": pl.Int64},
                "output_length": 6,
            },
            id="int64_input",
        ),
        pytest.param(
            {
                "input": "85283473fffffff",
                "schema": None,
                "output_length": 6,
            },
            id="string_input",
        ),
    ],
)
def test_origin_to_directed_edges(test_params):
    df = pl.DataFrame(
        {"h3_cell": [test_params["input"]]},
        schema=test_params["schema"],
    ).with_columns(edges=polars_h3.origin_to_directed_edges("h3_cell"))
    assert len(df["edges"][0]) == test_params["output_length"]


def test_directed_edge_operations():
    # Test edge to cells conversion
    df = pl.DataFrame(
        {"edge": [1608492358964346879], "edge_str": ["165283473fffffff"]}
    ).with_columns(
        [
            polars_h3.directed_edge_to_cells("edge").alias("cells_int"),
            polars_h3.directed_edge_to_cells("edge_str").alias("cells_str"),
        ]
    )

    assert len(df["cells_int"][0]) == 2
    assert len(df["cells_str"][0]) == 2

    # Test invalid edge
    df_invalid = pl.DataFrame({"edge": [0]}).with_columns(
        cells=polars_h3.directed_edge_to_cells("edge")
    )
    assert df_invalid["cells"][0] is None

    # Test origin and destination
    df_endpoints = pl.DataFrame({"edge": [1608492358964346879]}).with_columns(
        [
            polars_h3.get_directed_edge_origin("edge").alias("origin"),
            polars_h3.get_directed_edge_destination("edge").alias("destination"),
        ]
    )
    assert df_endpoints["origin"][0] == 599686042433355775
    assert df_endpoints["destination"][0] == 599686030622195711


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input_1": 599686042433355775,
                "input_2": 599686030622195711,
                "schema": {"cell1": pl.UInt64, "cell2": pl.UInt64},
                "output": True,
            },
            id="neighbor_uint64",
        ),
        pytest.param(
            {
                "input_1": 599686042433355775,
                "input_2": 599686029548453887,
                "schema": {"cell1": pl.UInt64, "cell2": pl.UInt64},
                "output": False,
            },
            id="not_neighbor_uint64",
        ),
        pytest.param(
            {
                "input_1": "85283473fffffff",
                "input_2": "85283447fffffff",
                "schema": None,
                "output": True,
            },
            id="neighbor_str",
        ),
        pytest.param(
            {
                "input_1": "85283473fffffff",
                "input_2": "85283443fffffff",
                "schema": None,
                "output": False,
            },
            id="not_neighbor_str",
        ),
    ],
)
def test_are_neighbor_cells(test_params):
    df = pl.DataFrame(
        {
            "cell1": [test_params["input_1"]],
            "cell2": [test_params["input_2"]],
        },
        schema=test_params["schema"],
    ).with_columns(neighbors=polars_h3.are_neighbor_cells("cell1", "cell2"))
    assert df["neighbors"][0] == test_params["output"]


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input_1": 599686042433355775,
                "input_2": 599686030622195711,
                "schema": {"origin": pl.UInt64, "destination": pl.UInt64},
                "output": 1608492358964346879,
            },
            id="int_edge",
        ),
        pytest.param(
            {
                "input_1": "85283473fffffff",
                "input_2": "85283447fffffff",
                "schema": None,
                "output": 1608492358964346879,
            },
            id="string_edge",
        ),
    ],
)
def test_cells_to_directed_edge(test_params):
    df = pl.DataFrame(
        {
            "origin": [test_params["input_1"]],
            "destination": [test_params["input_2"]],
        },
        schema=test_params["schema"],
    ).with_columns(edge=polars_h3.cells_to_directed_edge("origin", "destination"))
    assert df["edge"][0] == test_params["output"]
