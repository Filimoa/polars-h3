"""Behavior across slices, null bitmaps, chunk boundaries, and execution modes."""

import math

import h3.api.basic_int as reference
import polars as pl
import pytest
from polars.testing import assert_frame_equal

import polars_h3 as h3


def collect(frame, expressions, mode):
    if mode == "eager":
        return frame.select(expressions)
    return frame.lazy().select(expressions).collect(engine=mode)


def fragment(series, size):
    return pl.concat(
        [series.slice(start, size) for start in range(0, len(series), size)],
        rechunk=False,
    )


@pytest.mark.parametrize("mode", ["eager", "auto", "streaming"])
@pytest.mark.parametrize("dtype", [pl.UInt64, pl.Int64, pl.String])
def test_cell_kernels_preserve_invalids_and_sliced_nulls(dtype, mode):
    cell = reference.latlng_to_cell(37.77527, -122.4183, 9)
    pentagon = reference.get_pentagons(9)[0]
    values = [cell, None, 0, pentagon, cell, None, 1] * 6000
    if dtype == pl.String:
        values = [format(v, "x") if v is not None else None for v in values]
        values[16] = "not-hex"
    elif dtype == pl.Int64:
        values[16] = -1
    else:
        values[16] = 2**64 - 1
    series = pl.Series("cell", values, dtype=dtype)
    frame = fragment(series, 997).slice(13, 40_003).to_frame()
    exprs = [
        h3.get_resolution("cell").alias("resolution"),
        h3.is_pentagon("cell").alias("pentagon"),
        h3.is_res_class_III("cell").alias("class_iii"),
        h3.cell_to_parent("cell", 8).alias("parent"),
        h3.cell_to_center_child("cell", 10).alias("center_child"),
        h3.cell_to_children_size("cell", 10).alias("children_size"),
        h3.cell_to_child_pos("cell", 8).alias("child_pos"),
    ]
    expected = {
        name: []
        for name in [
            "resolution",
            "pentagon",
            "class_iii",
            "parent",
            "center_child",
            "children_size",
            "child_pos",
        ]
    }
    for value in frame["cell"]:
        try:
            integer = int(value, 16) if isinstance(value, str) else value
            valid = (
                integer is not None
                and integer >= 0
                and reference.is_valid_cell(integer)
            )
        except ValueError:
            valid = False
        if not valid:
            for key in expected:
                expected[key].append(
                    False if key in {"pentagon", "class_iii"} else None
                )
            continue
        expected["resolution"].append(reference.get_resolution(integer))
        expected["pentagon"].append(reference.is_pentagon(integer))
        expected["class_iii"].append(reference.is_res_class_III(integer))
        parent = reference.cell_to_parent(integer, 8)
        child = reference.cell_to_center_child(integer, 10)
        expected["parent"].append(format(parent, "x") if dtype == pl.String else parent)
        expected["center_child"].append(
            format(child, "x") if dtype == pl.String else child
        )
        expected["children_size"].append(reference.cell_to_children_size(integer, 10))
        expected["child_pos"].append(reference.cell_to_child_pos(integer, 8))
    expected = pl.DataFrame(
        expected,
        schema={
            "resolution": pl.UInt32,
            "pentagon": pl.Boolean,
            "class_iii": pl.Boolean,
            "parent": dtype,
            "center_child": dtype,
            "children_size": pl.UInt64,
            "child_pos": pl.UInt64,
        },
    )
    assert_frame_equal(collect(frame, exprs, mode), expected)
    assert_frame_equal(collect(frame.rechunk(), exprs, mode), expected)


@pytest.mark.parametrize("mode", ["eager", "auto", "streaming"])
@pytest.mark.parametrize(
    "lat_dtype,lng_dtype",
    [(pl.Float64, pl.Float64), (pl.Float32, pl.Float64), (pl.Float64, pl.Float32)],
)
def test_coordinate_kernels_align_chunks_and_validate_finite_values(
    lat_dtype, lng_dtype, mode
):
    lat = pl.Series(
        "lat",
        [37.77527, None, 0.0, 89.5, float("nan"), float("inf"), float("-inf"), 42.0]
        * 6000,
        dtype=lat_dtype,
    )
    lng = pl.Series(
        "lng",
        [-122.4183, 10.0, None, 80.0, 30.0, 40.0, 50.0, -81.0] * 6000,
        dtype=lng_dtype,
    )
    frame = pl.DataFrame([fragment(lat, 997), fragment(lng, 701)]).slice(13, 40_003)
    expected = []
    for latitude, longitude in frame.iter_rows():
        if (
            latitude is None
            or longitude is None
            or not math.isfinite(latitude)
            or not math.isfinite(longitude)
        ):
            expected.append(None)
        else:
            expected.append(reference.latlng_to_cell(latitude, longitude, 9))
    expected = pl.DataFrame(
        {
            "cell": pl.Series(expected, dtype=pl.UInt64),
            "string": [format(v, "x") if v is not None else None for v in expected],
        }
    )
    exprs = [
        h3.latlng_to_cell("lat", "lng", 9).alias("cell"),
        h3.latlng_to_cell("lat", "lng", 9, return_dtype=pl.String).alias("string"),
    ]
    assert_frame_equal(collect(frame, exprs, mode), expected)
    assert_frame_equal(collect(frame.rechunk(), exprs, mode), expected)


@pytest.mark.parametrize("dtype", [pl.UInt64, pl.Int64, pl.String])
def test_cell_coordinates_match_reference_across_batches(dtype):
    cells = [
        reference.latlng_to_cell(37.7, -122.4, 9),
        None,
        0,
        reference.get_pentagons(9)[0],
    ] * 10_001
    values = (
        [format(v, "x") if v is not None else None for v in cells]
        if dtype == pl.String
        else cells
    )
    frame = pl.DataFrame({"cell": pl.Series(values, dtype=dtype)}).slice(3, 40_000)
    out = frame.select(
        lat=h3.cell_to_lat("cell"),
        lng=h3.cell_to_lng("cell"),
        coords=h3.cell_to_latlng("cell"),
    )
    for cell, row in zip(cells[3:40_003], out.iter_rows(), strict=True):
        if cell is None or cell == 0:
            assert row == (None, None, None)
        else:
            lat, lng = reference.cell_to_latlng(cell)
            assert row[0] == pytest.approx(lat, abs=1e-10)
            assert row[1] == pytest.approx(lng, abs=1e-10)
            assert row[2] == pytest.approx([lat, lng], abs=1e-10)


def test_indexing_pipeline_does_not_multiply_output_chunks():
    rows = 200_000
    frame = pl.DataFrame({"i": pl.int_range(0, rows, eager=True)}).select(
        lat=37.7 + pl.col("i") % 100 / 1000,
        lng=-122.4 + pl.col("i") % 117 / 1000,
    )
    query = (
        frame.lazy()
        .select(cell=h3.latlng_to_cell("lat", "lng", 9))
        .with_columns(
            parent=h3.cell_to_parent("cell", 8),
            resolution=h3.get_resolution("cell"),
        )
    )
    out = query.collect()
    assert out.height == rows
    assert out["resolution"].to_list() == [9] * rows
    # Allow engine partitioning while catching the previous thousands of chunks.
    assert max(out.n_chunks(strategy="all")) <= 256


@pytest.mark.parametrize("rows", [0, 40_000])
def test_empty_and_all_null_coordinates(rows):
    frame = pl.DataFrame(
        {
            "lat": pl.Series([None] * rows, dtype=pl.Float64),
            "lng": pl.Series([None] * rows, dtype=pl.Float32),
        }
    )
    out = frame.select(
        cell=h3.latlng_to_cell("lat", "lng", 9),
        string=h3.latlng_to_cell("lat", "lng", 9, return_dtype=pl.String),
    )
    assert out.schema == {"cell": pl.UInt64, "string": pl.String}
    assert out.height == rows
    assert out.null_count().row(0) == (rows, rows)
