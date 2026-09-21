"""Row-wise plugins must preserve results across Polars execution contexts."""

from functools import partial

import h3.api.basic_int as h3
import polars as pl
import pytest
from polars.testing import assert_frame_equal

import polars_h3 as plh3

CELL = h3.latlng_to_cell(37.77, -122.42, 5)
PENTAGON = h3.get_pentagons(5)[0]


@pytest.mark.parametrize(
    "function,values",
    [
        (
            plh3.is_valid_directed_edge,
            [h3.origin_to_directed_edges(c)[0] for c in (CELL, PENTAGON)],
        ),
        (
            plh3.get_directed_edge_origin,
            [h3.origin_to_directed_edges(c)[0] for c in (CELL, PENTAGON)],
        ),
        (
            plh3.get_directed_edge_destination,
            [h3.origin_to_directed_edges(c)[0] for c in (CELL, PENTAGON)],
        ),
        (
            plh3.directed_edge_to_cells,
            [h3.origin_to_directed_edges(c)[0] for c in (CELL, PENTAGON)],
        ),
        (
            plh3.directed_edge_to_boundary,
            [h3.origin_to_directed_edges(c)[0] for c in (CELL, PENTAGON)],
        ),
        (plh3.origin_to_directed_edges, [CELL, PENTAGON]),
        (partial(plh3.cell_to_vertex, vertex_num=0), [CELL, PENTAGON]),
        (plh3.cell_to_vertexes, [CELL, PENTAGON]),
        (plh3.vertex_to_latlng, [h3.cell_to_vertex(c, 0) for c in (CELL, PENTAGON)]),
        (plh3.is_valid_vertex, [h3.cell_to_vertex(c, 0) for c in (CELL, PENTAGON)]),
    ],
    ids=[
        "is_valid_directed_edge",
        "get_directed_edge_origin",
        "get_directed_edge_destination",
        "directed_edge_to_cells",
        "directed_edge_to_boundary",
        "origin_to_directed_edges",
        "cell_to_vertex",
        "cell_to_vertexes",
        "vertex_to_latlng",
        "is_valid_vertex",
    ],
)
@pytest.mark.parametrize("dtype", [pl.UInt64, pl.Int64, pl.String])
@pytest.mark.parametrize("case", ["mixed", "null", "empty"])
def test_elementwise_execution_contexts(function, values, dtype, case):
    values = (values + [None, 0]) * 8 if case == "mixed" else [None] * 8
    if case == "empty":
        values = []
    if dtype == pl.String:
        values = [format(v, "x") if v is not None else None for v in values]
    df = pl.DataFrame({"value": pl.Series(values, dtype=dtype)}).with_row_index()
    df = df.with_columns((pl.col("index") % 3).alias("group"))
    df = pl.concat([df[:5], df[5:]], rechunk=False)
    expression = function("value").alias("result")
    expected = df.with_columns(expression)

    assert_frame_equal(
        df.lazy().with_columns(expression).collect(engine="streaming"), expected
    )
    # Precomputing before grouping avoids depending on plugin group execution
    # for the expected value (including nested list-valued aggregations).
    assert_frame_equal(
        df.lazy().group_by("group").agg(expression).sort("group").collect(),
        expected.group_by("group").agg("result").sort("group"),
    )
    assert_frame_equal(df.select(expression.over("group")), expected.select("result"))
    assert_frame_equal(
        df.lazy().with_columns(expression).slice(1, 7).collect(), expected.slice(1, 7)
    )
