"""Scalar fusion must preserve null alignment, H3 semantics and string output."""

import h3.api.basic_int as reference
import polars as pl
import pytest
from h3 import H3BaseException
from polars.testing import assert_frame_equal

import polars_h3 as h3
from tests.test_kernel_batches import collect, fragment


def encode(values, dtype):
    if dtype == pl.String:
        return [
            "not-hex" if v == 0 else format(v, "x") if v is not None else None
            for v in values
        ]
    return [(-1 if dtype == pl.Int64 else 2**64 - 1) if v == 0 else v for v in values]


def safe_call(fn, *args):
    if any(v is None or v == 0 for v in args):
        return None
    try:
        return fn(*args)
    except (ValueError, H3BaseException):
        return None


@pytest.mark.parametrize("mode", ["eager", "auto", "streaming"])
@pytest.mark.parametrize("dtype", [pl.UInt64, pl.Int64, pl.String])
@pytest.mark.parametrize("dest_dtype", [pl.UInt64, pl.Int64, pl.String])
def test_paired_edge_vertex_kernels(dtype, dest_dtype, mode):
    cell = reference.latlng_to_cell(37.7, -122.4, 9)
    neighbor = next(v for v in reference.grid_disk(cell, 1) if v != cell)
    pentagon = reference.get_pentagons(9)[0]
    pent_neighbor = next(v for v in reference.grid_disk(pentagon, 1) if v != pentagon)
    origins = [cell, None, 0, pentagon, cell, cell, cell, cell]
    destinations = [neighbor, cell, cell, pent_neighbor, None, 0, cell, pentagon]
    edge = reference.cells_to_directed_edge(cell, neighbor)
    pent_edge = reference.cells_to_directed_edge(pentagon, pent_neighbor)
    edges = [edge, None, 0, pent_edge, edge, edge, 0, edge]
    vertices = [
        reference.cell_to_vertex(cell, 0),
        None,
        0,
        reference.cell_to_vertex(pentagon, 0),
        0,
        None,
        0,
        0,
    ]
    positions = [0, 0, 0, 0, None, 999, 6, 1]
    expected = {
        name: []
        for name in [
            "neighbor",
            "edge",
            "distance",
            "vertex",
            "valid_vertex",
            "origin",
            "destination",
            "child",
        ]
    }
    for org, dst, edg, vtx, pos in zip(
        origins, destinations, edges, vertices, positions, strict=True
    ):
        expected["neighbor"].append(
            bool(safe_call(reference.are_neighbor_cells, org, dst))
        )
        expected["edge"].append(safe_call(reference.cells_to_directed_edge, org, dst))
        expected["distance"].append(safe_call(reference.grid_distance, org, dst))
        expected["vertex"].append(reference.cell_to_vertex(org, 0) if org else None)
        expected["valid_vertex"].append(bool(vtx and reference.is_valid_vertex(vtx)))
        expected["origin"].append(safe_call(reference.get_directed_edge_origin, edg))
        expected["destination"].append(
            safe_call(reference.get_directed_edge_destination, edg)
        )
        if org and pos is not None:
            try:
                child = reference.child_pos_to_cell(org, 10, pos)
            except (ValueError, H3BaseException):
                child = None
        else:
            child = None
        expected["child"].append(child)
    expected["child"] = encode(expected["child"], dtype)
    repeats = 4200
    frame = pl.DataFrame(
        [
            fragment(
                pl.Series("cell", encode(origins, dtype) * repeats, dtype=dtype), 997
            ),
            fragment(
                pl.Series(
                    "dest", encode(destinations, dest_dtype) * repeats, dtype=dest_dtype
                ),
                701,
            ),
            fragment(
                pl.Series("edge", encode(edges, dtype) * repeats, dtype=dtype), 503
            ),
            fragment(
                pl.Series("vertex", encode(vertices, dtype) * repeats, dtype=dtype), 809
            ),
            pl.Series("pos", positions * repeats, dtype=pl.UInt64),
        ]
    ).slice(13, 33001)
    expected = pl.DataFrame(
        {name: vals * repeats for name, vals in expected.items()},
        schema={
            "neighbor": pl.Boolean,
            "edge": pl.UInt64,
            "distance": pl.Int32,
            "vertex": pl.UInt64,
            "valid_vertex": pl.Boolean,
            "origin": pl.UInt64,
            "destination": pl.UInt64,
            "child": dtype,
        },
    ).slice(13, 33001)
    exprs = [
        h3.are_neighbor_cells("cell", "dest").alias("neighbor"),
        h3.cells_to_directed_edge("cell", "dest").alias("edge"),
        h3.grid_distance("cell", "dest").alias("distance"),
        h3.cell_to_vertex("cell", 0).alias("vertex"),
        h3.is_valid_vertex("vertex").alias("valid_vertex"),
        h3.get_directed_edge_origin("edge").alias("origin"),
        h3.get_directed_edge_destination("edge").alias("destination"),
        h3.child_pos_to_cell("cell", "pos", 10).alias("child"),
    ]
    assert_frame_equal(collect(frame, exprs, mode), expected)
    assert_frame_equal(collect(frame.rechunk(), exprs, mode), expected)


@pytest.mark.parametrize("rows", [0, 262143, 262144, 262145])
def test_large_scalar_threshold_and_string_lists(rows):
    cell = reference.latlng_to_cell(37.7, -122.4, 9)
    frame = pl.DataFrame({"cell": pl.Series([cell] * rows, dtype=pl.UInt64)})
    out = frame.select(
        parent=h3.cell_to_parent("cell", 8),
        center=h3.cell_to_center_child("cell", 10),
        size=h3.cell_to_children_size("cell", 10),
    )
    assert out.to_dict(as_series=False) == {
        "parent": [reference.cell_to_parent(cell, 8)] * rows,
        "center": [reference.cell_to_center_child(cell, 10)] * rows,
        "size": [7] * rows,
    }
    # Shared hexadecimal formatting is also used by nested list conversions.
    strings = pl.DataFrame(
        {"cell": pl.Series([format(cell, "x"), None, "0"], dtype=pl.String)}
    )
    lists = strings.select(h3.cell_to_children("cell", 10)).to_series().to_list()
    assert lists == [
        [format(v, "x") for v in reference.cell_to_children(cell, 10)],
        None,
        None,
    ]
