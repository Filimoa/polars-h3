"""Check the correctness gate and deterministic input/layout contract."""

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from benchmarks.head_to_head import cases, make_frame, validate


def test_benchmark_validation_rejects_different_cells_and_nulls():
    case = cases(9, 3)["cell_to_parent"]
    expected = pl.DataFrame({"result": pl.Series([1, None, 3], dtype=pl.UInt64)})
    validate(case, expected, expected.cast(pl.Int64))
    for values in ([1, 2, 3], [1, None, 4]):
        with pytest.raises(AssertionError):
            validate(case, expected, pl.DataFrame({"result": values}))


def test_benchmark_normalizes_only_unordered_lists():
    suite = cases(9, 3)
    left = pl.DataFrame({"result": [[1, 2, 3]]})
    right = pl.DataFrame({"result": [[3, 2, 1]]})
    validate(suite["grid_disk"], left, right)
    with pytest.raises(AssertionError):
        validate(suite["directed_edge_to_cells"], left, right)


def test_benchmark_dataset_is_deterministic_across_layouts():
    case = cases(9, 3)["latlng_to_cell"]
    expected = make_frame(case, 65543, 9, "contiguous", 7)
    assert expected.height == 65543
    assert expected["lat"].null_count() == 9364
    for layout in ("chunked", "sliced"):
        actual = make_frame(case, 65543, 9, layout, 7)
        assert_frame_equal(actual, expected)
    assert make_frame(case, 65543, 9, "chunked", 0).n_chunks() == 2
    generated = cases(9, 3)["cell_to_parent"]
    assert make_frame(generated, 65543, 9, "contiguous", 0).n_chunks() == 1
    assert make_frame(generated, 65543, 9, "chunked", 0).n_chunks() == 2


def test_coordinate_validation_checks_structure_and_every_value():
    case = cases(9, 3)["cell_to_latlng"]

    def frame(values):
        return pl.DataFrame({"result": pl.Series(values, dtype=pl.List(pl.Float64))})

    expected = frame([[1.0, 2.0], None, [3.0, 4.0]])
    validate(case, expected, frame([[1.0 + 1e-10, 2.0], None, [3.0, 4.0]]))
    for values in (
        [[1.0, 2.0], None, [3.0, 5.0]],
        [[1.0], [2.0], [3.0, 4.0]],
        [[1.0, 2.0], [None], [3.0, 4.0]],
    ):
        with pytest.raises(AssertionError):
            validate(case, expected, frame(values))
