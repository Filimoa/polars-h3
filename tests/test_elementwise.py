import polars as pl
import pytest
from polars.testing import assert_frame_equal

import polars_h3 as plh3

EDGE_ORIGIN = 599686042433355775
EDGE_DESTINATION = 599686030622195711
DIRECTED_EDGE = 1608492358964346879
GRID_ORIGIN = 605035864166236159
GRID_DESTINATION = 605034941150920703
LOCAL_ORIGIN = 605034941285138431


@pytest.fixture
def broadcast_df() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "edge_origin": [EDGE_ORIGIN] * 3,
            "grid_origin": [GRID_ORIGIN] * 3,
            "local_cell": [LOCAL_ORIGIN] * 3,
            "k": [0, 1, 2],
            "i": [-123] * 3,
            "j": [-177] * 3,
        },
        schema={
            "edge_origin": pl.UInt64,
            "grid_origin": pl.UInt64,
            "local_cell": pl.UInt64,
            "k": pl.Int32,
            "i": pl.Int32,
            "j": pl.Int32,
        },
    )


def elementwise_cases():
    return [
        pytest.param(
            plh3.grid_distance(
                "grid_origin", pl.lit(GRID_DESTINATION, dtype=pl.UInt64)
            ),
            [5, 5, 5],
            False,
            id="grid_distance",
        ),
        pytest.param(
            plh3.grid_ring(pl.lit(EDGE_ORIGIN, dtype=pl.UInt64), "k"),
            [1, 6, 12],
            True,
            id="grid_ring",
        ),
        pytest.param(
            plh3.grid_disk(pl.lit(EDGE_ORIGIN, dtype=pl.UInt64), "k"),
            [1, 7, 19],
            True,
            id="grid_disk",
        ),
        pytest.param(
            plh3.grid_path_cells(
                "grid_origin", pl.lit(GRID_DESTINATION, dtype=pl.UInt64)
            ),
            [6, 6, 6],
            True,
            id="grid_path_cells",
        ),
        pytest.param(
            plh3.cell_to_local_ij("local_cell", pl.lit(LOCAL_ORIGIN, dtype=pl.UInt64)),
            [[-123.0, -177.0]] * 3,
            False,
            id="cell_to_local_ij",
        ),
        pytest.param(
            plh3.local_ij_to_cell(pl.lit(LOCAL_ORIGIN, dtype=pl.UInt64), "i", "j"),
            [LOCAL_ORIGIN] * 3,
            False,
            id="local_ij_to_cell",
        ),
        pytest.param(
            plh3.are_neighbor_cells(
                "edge_origin", pl.lit(EDGE_DESTINATION, dtype=pl.UInt64)
            ),
            [True, True, True],
            False,
            id="are_neighbor_cells",
        ),
        pytest.param(
            plh3.cells_to_directed_edge(
                "edge_origin", pl.lit(EDGE_DESTINATION, dtype=pl.UInt64)
            ),
            [DIRECTED_EDGE] * 3,
            False,
            id="cells_to_directed_edge",
        ),
    ]


@pytest.mark.parametrize("expression,expected,list_lengths", elementwise_cases())
def test_elementwise_functions_broadcast_scalar_inputs(
    broadcast_df: pl.DataFrame,
    expression: pl.Expr,
    expected,
    list_lengths: bool,
):
    result = broadcast_df.select(expression.alias("result"))["result"]

    if list_lengths:
        assert result.list.len().to_list() == expected
    else:
        assert result.to_list() == expected


@pytest.mark.parametrize("expression", [case.values[0] for case in elementwise_cases()])
def test_elementwise_functions_are_slice_pushdown_safe(
    broadcast_df: pl.DataFrame, expression: pl.Expr
):
    query = broadcast_df.lazy().select(expression.alias("result")).slice(1, 1)

    with_slice_pushdown = query.collect(slice_pushdown=True)
    without_slice_pushdown = query.collect(slice_pushdown=False)

    assert with_slice_pushdown.height == 1
    assert_frame_equal(with_slice_pushdown, without_slice_pushdown)


@pytest.mark.parametrize(
    "data,schema,expression",
    [
        pytest.param(
            {"origin": []},
            {"origin": pl.UInt64},
            plh3.grid_distance("origin", pl.lit(GRID_DESTINATION, dtype=pl.UInt64)),
            id="scalar_destination",
        ),
        pytest.param(
            {"k": []},
            {"k": pl.Int32},
            plh3.grid_ring(pl.lit(EDGE_ORIGIN, dtype=pl.UInt64), "k"),
            id="scalar_cell",
        ),
        pytest.param(
            {"origin": []},
            {"origin": pl.UInt64},
            plh3.local_ij_to_cell("origin", pl.lit(-123), pl.lit(-177)),
            id="scalar_coordinates",
        ),
    ],
)
def test_elementwise_functions_broadcast_over_empty_columns(
    data, schema, expression: pl.Expr
):
    result = pl.DataFrame(data, schema=schema).select(expression.alias("result"))

    assert result.height == 0
