"""Exercise validity and chunk offsets across parallel batch boundaries."""

import math
import random

import h3.api.basic_int as h3
import polars as pl
import pytest
from polars.testing import assert_series_equal

import polars_h3 as h

CELL = h3.latlng_to_cell(37.77, -122.42, 9)
PENTAGON = h3.get_pentagons(9)[0]


@pytest.mark.parametrize("resolution", [0, 1, 5, 9, 15])
def test_global_coordinate_batches_against_reference(resolution):
    rng = random.Random(42)
    points = [(rng.uniform(-89.9, 89.9), rng.uniform(-180, 180)) for _ in range(1025)]
    expected = [h3.latlng_to_cell(lat, lng, resolution) for lat, lng in points]
    # Cross the sequential/parallel threshold and multiple batch boundaries.
    frame = pl.DataFrame(points * 33, schema=["lat", "lng"], orient="row")
    actual = frame.select(h.latlng_to_cell("lat", "lng", resolution)).to_series()
    assert_series_equal(actual, pl.Series("lat", expected * 33, dtype=pl.UInt64))
    centers = [list(h3.cell_to_latlng(cell)) for cell in expected]
    assert_series_equal(
        actual.to_frame().select(h.cell_to_latlng("lat")).to_series(),
        pl.Series("lat", centers * 33, dtype=pl.List(pl.Float64)),
        check_exact=False,
    )


@pytest.mark.parametrize("dtype", [pl.UInt64, pl.Int64, pl.String])
@pytest.mark.parametrize("layout", ["contiguous", "chunked", "sliced"])
def test_large_cell_batches(dtype, layout):
    pattern = [CELL, None, 0, PENTAGON, 2**63 - 1]
    values = (pattern * 26216)[:131079]
    if dtype == pl.String:
        values = [format(v, "x") if v is not None else None for v in values]
    series = pl.Series("cell", values, dtype=dtype)
    if layout == "chunked":
        series = pl.concat(
            [series[:13], series[13:65539], series[65539:]], rechunk=False
        )
    elif layout == "sliced":
        series = pl.concat([series.head(3), series], rechunk=True).slice(3)
    frame = series.to_frame()
    specifications = [
        (h.get_resolution("cell"), h3.get_resolution, pl.UInt32, None),
        (h.is_valid_cell("cell"), lambda _: True, pl.Boolean, False),
        (h.is_pentagon("cell"), h3.is_pentagon, pl.Boolean, False),
        (h.is_res_class_III("cell"), h3.is_res_class_III, pl.Boolean, False),
        (h.cell_to_lat("cell"), lambda c: h3.cell_to_latlng(c)[0], pl.Float64, None),
        (h.cell_to_lng("cell"), lambda c: h3.cell_to_latlng(c)[1], pl.Float64, None),
        (
            h.cell_to_children_size("cell", 10),
            lambda c: h3.cell_to_children_size(c, 10),
            pl.UInt64,
            None,
        ),
        (
            h.cell_to_child_pos("cell", 8),
            lambda c: h3.cell_to_child_pos(c, 8),
            pl.UInt64,
            None,
        ),
    ]
    for expression, oracle, output_dtype, invalid in specifications:
        expected_pattern = [oracle(CELL), invalid, invalid, oracle(PENTAGON), invalid]
        expected = pl.Series(
            "cell", (expected_pattern * 26216)[: len(series)], dtype=output_dtype
        )
        assert_series_equal(
            frame.select(expression).to_series(), expected, check_exact=False
        )

    for expression, oracle in [
        (h.cell_to_parent("cell", 8), lambda c: h3.cell_to_parent(c, 8)),
        (h.cell_to_center_child("cell", 10), lambda c: h3.cell_to_center_child(c, 10)),
    ]:
        expected_pattern = [oracle(CELL), None, None, oracle(PENTAGON), None]
        if dtype == pl.String:
            expected_pattern = [
                format(v, "x") if v is not None else None for v in expected_pattern
            ]
        expected = pl.Series(
            "cell", (expected_pattern * 26216)[: len(series)], dtype=dtype
        )
        assert_series_equal(frame.select(expression).to_series(), expected)


@pytest.mark.parametrize("dtype", [pl.Float32, pl.Float64])
def test_coordinate_batches_with_independent_chunk_and_null_offsets(dtype):
    lat = pl.Series(
        "lat", [37.77, None, float("nan"), float("inf"), -33.86] * 26216, dtype=dtype
    )
    lng = pl.Series("lng", [-122.42, 0.0, 1.0, 1.0, 151.21] * 26216, dtype=dtype)
    lat = pl.concat([lat[:65539], lat[65539:]], rechunk=False).slice(3, 131073)
    lng = pl.concat([lng[:17], lng[17:]], rechunk=False).slice(3, 131073)
    # Compute the five possible results with the independent reference library,
    # including Float32 rounding before conversion.
    expected = []
    for a, b in zip(lat.head(5), lng.head(5), strict=True):
        expected.append(
            h3.latlng_to_cell(a, b, 9) if a is not None and math.isfinite(a) else None
        )
    expected = (expected * 26216)[: len(lat)]
    frame = pl.DataFrame([lat, lng])
    assert_series_equal(
        frame.select(h.latlng_to_cell("lat", "lng", 9)).to_series(),
        pl.Series("lat", expected, dtype=pl.UInt64),
    )
    assert_series_equal(
        frame.select(
            h.latlng_to_cell("lat", "lng", 9, return_dtype=pl.String)
        ).to_series(),
        pl.Series(
            "lat",
            [format(v, "x") if v is not None else None for v in expected],
            dtype=pl.String,
        ),
    )


def test_scalar_outputs_do_not_fragment_into_thousands_of_chunks():
    frame = pl.DataFrame(
        {"cell": pl.repeat(CELL, 200_000, dtype=pl.UInt64, eager=True)}
    )
    for expression in [
        h.get_resolution("cell"),
        h.cell_to_lat("cell"),
        h.cell_to_parent("cell", 8),
    ]:
        result = frame.select(expression)
        assert result.n_chunks() <= max(64, pl.thread_pool_size() * 4)


@pytest.mark.parametrize("dtype", [pl.UInt64, pl.Int64, pl.String])
def test_binary_and_edge_batches(dtype):
    neighbor = h3.grid_ring(CELL, 1)[0]
    pent_neighbor = h3.get_directed_edge_destination(
        h3.origin_to_directed_edges(PENTAGON)[0]
    )
    edge = h3.cells_to_directed_edge(CELL, neighbor)
    pent_edge = h3.cells_to_directed_edge(PENTAGON, pent_neighbor)
    rows = 131079

    def repeated(name, pattern, output_dtype):
        values = (pattern * (rows // len(pattern) + 1))[:rows]
        if output_dtype == pl.String:
            values = [format(v, "x") if v is not None else None for v in values]
        return pl.Series(name, values, dtype=output_dtype)

    left = repeated("left", [CELL, None, 0, PENTAGON, CELL, CELL], dtype)
    right = repeated(
        "right", [neighbor, neighbor, neighbor, pent_neighbor, None, 0], dtype
    )
    edges = repeated("edge", [edge, None, 0, pent_edge, None, 0], dtype)
    frame = pl.DataFrame(
        [
            pl.concat([left[:13], left[13:]], rechunk=False),
            pl.concat([right[:65539], right[65539:]], rechunk=False),
            edges,
        ]
    )
    checks = [
        (
            h.grid_distance("left", "right"),
            [1, None, None, 1, None, None],
            pl.Int32,
            "left",
        ),
        (
            h.are_neighbor_cells("left", "right"),
            [True, False, False, True, False, False],
            pl.Boolean,
            "left",
        ),
        (
            h.cells_to_directed_edge("left", "right"),
            [edge, None, None, pent_edge, None, None],
            pl.UInt64,
            "left",
        ),
        (
            h.get_directed_edge_origin("edge"),
            [CELL, None, None, PENTAGON, None, None],
            pl.UInt64,
            "edge",
        ),
        (
            h.get_directed_edge_destination("edge"),
            [neighbor, None, None, pent_neighbor, None, None],
            pl.UInt64,
            "edge",
        ),
        (
            h.edge_length("edge"),
            [h3.edge_length(edge), None, None, h3.edge_length(pent_edge), None, None],
            pl.Float64,
            "edge",
        ),
    ]
    for expression, pattern, output_dtype, name in checks:
        expected = repeated(name, pattern, output_dtype)
        assert_series_equal(
            frame.select(expression).to_series(), expected, check_exact=False
        )


@pytest.mark.parametrize("dtype", [pl.UInt64, pl.Int64, pl.String])
def test_list_batches_preserve_empty_null_pentagon_and_order(dtype):
    values = [CELL, PENTAGON, None, 0] * 17001
    if dtype == pl.String:
        values = [format(v, "x") if v is not None else None for v in values]
    frame = pl.DataFrame({"cell": pl.Series(values, dtype=dtype)})
    for expression, oracle, inner_dtype in [
        (h.cell_to_children("cell", 10), lambda c: h3.cell_to_children(c, 10), dtype),
        (
            h.origin_to_directed_edges("cell"),
            # polars-h3 preserves numeric direction order; C H3 rotates the
            # starting edge for pentagons. The saved baseline has this order.
            lambda c: sorted(h3.origin_to_directed_edges(c)),
            pl.UInt64,
        ),
        (h.cell_to_vertexes("cell"), lambda c: h3.cell_to_vertexes(c), pl.UInt64),
    ]:
        expected = [oracle(CELL), oracle(PENTAGON), None, None]
        if inner_dtype == pl.String:
            expected = [
                [format(v, "x") for v in values] if values is not None else None
                for values in expected
            ]
        assert_series_equal(
            frame.select(expression).to_series(),
            pl.Series("cell", expected * 17001, dtype=pl.List(inner_dtype)),
        )
    result = frame.select(h.cell_to_children("cell", 8)).to_series()
    assert result.head(4).to_list() == [[], [], None, None]


@pytest.mark.parametrize("dtype", [pl.UInt64, pl.Int64, pl.String])
def test_grid_batches_reuse_scratch_without_leaking_partial_pentagon_results(dtype):
    cells = [CELL, PENTAGON, None, 0, CELL, CELL, CELL, CELL, PENTAGON]
    radii = [0, 1, 1, 2, -1, None, 2, 1, 0]
    repeats = 8000
    encoded = (
        [format(v, "x") if v is not None else None for v in cells]
        if dtype == pl.String
        else cells
    )
    frame = pl.DataFrame(
        {
            "cell": pl.Series(encoded * repeats, dtype=dtype),
            "k": pl.Series(radii * repeats, dtype=pl.Int32),
        }
    )
    checks = [
        (
            h.grid_disk("cell", "k"),
            [
                h3.grid_disk(CELL, 0),
                h3.grid_disk(PENTAGON, 1),
                None,
                None,
                None,
                None,
                h3.grid_disk(CELL, 2),
                h3.grid_disk(CELL, 1),
                h3.grid_disk(PENTAGON, 0),
            ],
        ),
        (
            h.grid_ring("cell", "k"),
            [
                [CELL],
                [],
                None,
                None,
                None,
                None,
                h3.grid_ring(CELL, 2),
                h3.grid_ring(CELL, 1),
                [PENTAGON],
            ],
        ),
        (
            h.grid_disk("cell", 1),
            [h3.grid_disk(c, 1) if c not in (None, 0) else None for c in cells],
        ),
    ]
    for expression, expected in checks:
        if dtype == pl.String:
            expected = [
                [format(v, "x") for v in row] if row is not None else None
                for row in expected
            ]
        expected = [sorted(row) if row is not None else None for row in expected]
        result = frame.select(expression).to_series()
        assert result.dtype == pl.List(dtype)
        assert [
            sorted(row) if row is not None else None for row in result.to_list()
        ] == expected * repeats


def test_disk_discards_partial_fast_traversal_near_a_pentagon():
    neighbor = h3.get_directed_edge_destination(
        h3.origin_to_directed_edges(PENTAGON)[0]
    )
    cells = [CELL, neighbor, CELL]
    frame = pl.DataFrame({"cell": pl.Series(cells * 23000, dtype=pl.UInt64)})
    expected = [sorted(h3.grid_disk(cell, 2)) for cell in cells]
    result = frame.select(h.grid_disk("cell", 2)).to_series().to_list()
    assert [sorted(row) for row in result] == expected * 23000
