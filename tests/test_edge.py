import pytest
import polars as pl

from typing import List, Dict, Union
import polars_h3


@pytest.mark.parametrize(
    "edge, schema, expected_valid",
    [
        pytest.param(["2222597fffffffff"], None, False, id="invalid_str_edge"),
        pytest.param([0], {"edge": pl.UInt64}, False, id="invalid_int_edge"),
        pytest.param(["115283473fffffff"], None, True, id="valid_str_edge"),
        pytest.param(
            [1248204388774707199], {"edge": pl.UInt64}, True, id="valid_int_edge"
        ),
    ],
)
def test_is_valid_directed_edge(
    edge: List[Union[int, str]],
    schema: Union[Dict[str, pl.DataType], None],
    expected_valid: bool,
):
    df = pl.DataFrame({"edge": edge}, schema=schema).with_columns(
        valid=polars_h3.is_valid_directed_edge("edge")
    )
    assert df["valid"][0] == expected_valid


@pytest.mark.parametrize(
    "origin_cell, schema",
    [
        pytest.param([599686042433355775], {"h3_cell": pl.UInt64}, id="uint64_input"),
        pytest.param([599686042433355775], {"h3_cell": pl.Int64}, id="int64_input"),
        pytest.param(["85283473fffffff"], None, id="string_input"),
    ],
)
def test_origin_to_directed_edges(
    origin_cell: List[Union[int, str]], schema: Union[Dict[str, pl.DataType], None]
):
    df = pl.DataFrame({"h3_cell": origin_cell}, schema=schema).with_columns(
        edges=polars_h3.origin_to_directed_edges("h3_cell")
    )
    assert len(df["edges"][0]) == 6  # Each cell should have 6 edges


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
    "cell1, cell2, schema, expected_neighbors",
    [
        pytest.param(
            [599686042433355775],
            [599686030622195711],
            {"cell1": pl.UInt64, "cell2": pl.UInt64},
            True,
            id="neighbor_uint64",
        ),
        pytest.param(
            [599686042433355775],
            [599686029548453887],
            {"cell1": pl.UInt64, "cell2": pl.UInt64},
            False,
            id="not_neighbor_uint64",
        ),
        pytest.param(
            ["85283473fffffff"], ["85283447fffffff"], None, True, id="neighbor_str"
        ),
        pytest.param(
            ["85283473fffffff"], ["85283443fffffff"], None, False, id="not_neighbor_str"
        ),
    ],
)
def test_are_neighbor_cells(
    cell1: List[Union[int, str]],
    cell2: List[Union[int, str]],
    schema: Union[Dict[str, pl.DataType], None],
    expected_neighbors: bool,
):
    df = pl.DataFrame({"cell1": cell1, "cell2": cell2}, schema=schema).with_columns(
        neighbors=polars_h3.are_neighbor_cells("cell1", "cell2")
    )
    assert df["neighbors"][0] == expected_neighbors


def test_cells_to_directed_edge():
    # Test with integers
    df_int = pl.DataFrame(
        {"origin": [599686042433355775], "destination": [599686030622195711]},
        schema={"origin": pl.UInt64, "destination": pl.UInt64},
    ).with_columns(edge=polars_h3.cells_to_directed_edge("origin", "destination"))
    assert df_int["edge"][0] == 1608492358964346879

    # Test with strings
    df_str = pl.DataFrame(
        {"origin": ["85283473fffffff"], "destination": ["85283447fffffff"]}
    ).with_columns(edge=polars_h3.cells_to_directed_edge("origin", "destination"))
    assert df_str["edge"][0] == 1608492358964346879
