import polars as pl
import pytest

import polars_h3 as plh3


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
    ).with_columns(valid=plh3.is_valid_directed_edge("edge"))
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
    ).with_columns(edges=plh3.origin_to_directed_edges("h3_cell"))
    assert len(df["edges"][0]) == test_params["output_length"]


def test_origin_to_directed_edges_preserves_direction_order():
    df = pl.DataFrame(
        {"h3_cell": [599686042433355775]},
        schema={"h3_cell": pl.UInt64},
    ).with_columns(edges=plh3.origin_to_directed_edges("h3_cell"))

    assert df["edges"][0].to_list() == [
        1248204388774707199,
        1320261982812635135,
        1392319576850563071,
        1464377170888491007,
        1536434764926418943,
        1608492358964346879,
    ]


def test_directed_edge_operations():
    # Test edge to cells conversion
    df = pl.DataFrame(
        {"edge": [1608492358964346879], "edge_str": ["165283473fffffff"]}
    ).with_columns(
        [
            plh3.directed_edge_to_cells("edge").alias("cells_int"),
            plh3.directed_edge_to_cells("edge_str").alias("cells_str"),
        ]
    )

    assert len(df["cells_int"][0]) == 2
    assert len(df["cells_str"][0]) == 2

    # Test invalid edge
    df_invalid = pl.DataFrame({"edge": [0]}).with_columns(
        cells=plh3.directed_edge_to_cells("edge")
    )
    assert df_invalid["cells"][0] is None

    # Test origin and destination
    df_endpoints = pl.DataFrame({"edge": [1608492358964346879]}).with_columns(
        [
            plh3.get_directed_edge_origin("edge").alias("origin"),
            plh3.get_directed_edge_destination("edge").alias("destination"),
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
    ).with_columns(neighbors=plh3.are_neighbor_cells("cell1", "cell2"))
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
    ).with_columns(edge=plh3.cells_to_directed_edge("origin", "destination"))
    assert df["edge"][0] == test_params["output"]


@pytest.mark.parametrize("dtype", [pl.UInt64, pl.Int64, pl.String])
@pytest.mark.parametrize("case", ["mixed", "null", "empty"])
def test_directed_edge_boundary_schema_and_execution(dtype, case):
    import h3.api.basic_int as h3
    from polars.testing import assert_frame_equal

    edge = 1608492358964346879
    values = [edge, None, 0] if case == "mixed" else [None]
    if case == "empty":
        values = []
    if dtype == pl.String:
        values = [format(v, "x") if v is not None else None for v in values]
    df = pl.DataFrame({"edge": pl.Series(values, dtype=dtype)}).with_columns(
        pl.lit(0).alias("group")
    )
    expression = plh3.directed_edge_to_boundary("edge").alias("boundary")
    query = df.lazy().select(expression)
    expected_values = (
        [
            [
                coordinate
                for point in h3.directed_edge_to_boundary(edge)
                for coordinate in point
            ],
            None,
            None,
        ]
        if case == "mixed"
        else [None]
        if case == "null"
        else []
    )
    expected = pl.DataFrame(
        {"boundary": pl.Series(expected_values, dtype=pl.List(pl.Float64))}
    )
    assert query.collect_schema() == expected.schema
    assert_frame_equal(query.collect(), expected)
    assert_frame_equal(query.collect(engine="streaming"), expected)
    precomputed = df.with_columns(expected["boundary"])
    grouped = df.lazy().group_by("group").agg(expression)
    assert (
        grouped.collect_schema() == precomputed.group_by("group").agg("boundary").schema
    )
    assert_frame_equal(grouped.collect(), precomputed.group_by("group").agg("boundary"))
    assert_frame_equal(df.select(expression.over("group")), expected)


def test_cell_boundary_keeps_nested_schema():
    query = (
        pl.DataFrame({"cell": [599686042433355775]})
        .lazy()
        .select(boundary=plh3.cell_to_boundary("cell"))
    )
    assert query.collect_schema()["boundary"] == pl.List(pl.List(pl.Float64))
    assert query.collect().schema == query.collect_schema()
