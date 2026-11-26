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


def test_samples_exclude_warmups_but_validate_them():
    from types import SimpleNamespace

    from benchmarks.common import collect_samples

    calls = []
    validated = []

    def run(engine):
        calls.append(engine)
        return pl.DataFrame({"result": [len(calls)]})

    samples = collect_samples(
        {"baseline": lambda: run("baseline"), "polars": lambda: run("polars")},
        SimpleNamespace(warmups=2, iterations=3),
        lambda output: validated.append(output.item()),
    )
    assert len(validated) == len(calls) == 10
    assert all(len(runs) == 3 for runs in samples.values())
    assert {tuple(calls[i : i + 2]) for i in range(0, len(calls), 2)} == {
        ("baseline", "polars"),
        ("polars", "baseline"),
    }


def test_invalid_warmup_aborts_measurement():
    from types import SimpleNamespace

    from benchmarks.common import collect_samples

    calls = []

    def run():
        calls.append(True)
        return pl.DataFrame({"result": [2]})

    def check(output):
        assert_frame_equal(pl.DataFrame({"result": [1]}), output)

    with pytest.raises(AssertionError):
        collect_samples(
            {"polars": run}, SimpleNamespace(warmups=1, iterations=3), check
        )
    assert len(calls) == 1


def test_report_preserves_failure_and_refuses_overwrite(tmp_path):
    import json

    from benchmarks.common import Report

    path = tmp_path / "results.json"
    with pytest.raises(ValueError, match="different output"):
        with Report(path, {"suite": "internal"}) as report:
            report.append({"name": "completed-case"})
            raise ValueError("different output")
    saved = json.loads(path.read_text())
    assert saved["status"] == "failed"
    assert saved["cases"] == [{"name": "completed-case"}]
    assert "different output" in saved["error"]
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        with Report(path, {}):
            pass
    assert path.read_bytes() == original
    with Report(tmp_path / "complete.json", {}) as report:
        report.append({"name": "ok"})
    assert json.loads((tmp_path / "complete.json").read_text())["status"] == "complete"


@pytest.mark.parametrize(
    "suite,count", [("duckdb", 33), ("internal", 46), ("python", 14), ("baselines", 6)]
)
def test_suite_listing_does_not_import_duckdb(suite, count):
    import subprocess
    import sys

    script = """
import importlib.abc, runpy, sys
class NoDuckDB(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        if fullname == 'duckdb':
            raise AssertionError('unexpected DuckDB dependency')
sys.meta_path.insert(0, NoDuckDB())
sys.argv = ['benchmarks', sys.argv[1], '--list']
runpy.run_module('benchmarks', run_name='__main__')
"""
    result = subprocess.run(
        [sys.executable, "-c", script, suite],
        capture_output=True,
        text=True,
        check=True,
    )
    assert len(result.stdout.splitlines()) == count


@pytest.mark.parametrize("suite", ["duckdb", "internal", "python", "baselines"])
def test_cli_rejects_bad_inputs_and_existing_evidence(tmp_path, suite):
    import subprocess
    import sys

    existing = tmp_path / "results.json"
    existing.write_text("do not overwrite")
    for flags, message in (
        (["--rows", "0"], "must be positive"),
        (["--output", str(existing)], "already exists"),
        (
            ["--output", str(tmp_path / "new.json"), "--functions", "typo"],
            "unknown functions",
        ),
    ):
        result = subprocess.run(
            [sys.executable, "-m", "benchmarks", suite, *flags],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert message in result.stderr
    assert existing.read_text() == "do not overwrite"
    assert not (tmp_path / "new.json").exists()


def test_python_suite_preserves_equivalent_full_outputs():
    from types import SimpleNamespace

    from benchmarks.python_api import cases as python_cases
    from benchmarks.python_api import python_expression

    args = SimpleNamespace(resolution=9, radius=3)
    for case in python_cases(9, 3).values():
        frame = make_frame(case, 8, 9, "contiguous", 0)
        expected = frame.select(case.expression().alias("result"))
        actual = frame.select(python_expression(case, args, expected.schema["result"]))
        validate(case, expected, actual)


def test_comparison_requires_complete_matched_measurements():
    from copy import deepcopy

    from benchmarks.compare_results import compare

    def result(engine, seconds):
        return {
            "engine": engine,
            "mode": "resident",
            "median_seconds": seconds,
            "min_seconds": seconds,
            "max_seconds": seconds,
        }

    report = {
        "status": "complete",
        "metadata": {"suite": "internal", "settings": {"threads": 2}},
        "cases": [
            {
                "name": "cell_to_parent",
                "rows": 128,
                "results": [result("baseline", 2), result("polars", 1)],
            }
        ],
    }
    assert compare(report, report, "baseline")[0]["improvement"] == 2
    assert compare(report, report, "baseline")[0]["duckdb_seconds"] is None
    for key, value in (("status", "failed"), ("status", "running")):
        other = deepcopy(report)
        other[key] = value
        with pytest.raises(ValueError, match="incomplete or failed"):
            compare(report, other)
    other = deepcopy(report)
    other["metadata"]["settings"]["threads"] = 8
    with pytest.raises(ValueError, match="different threads"):
        compare(report, other)
    other = deepcopy(report)
    other["cases"][0]["rows"] = 256
    with pytest.raises(ValueError, match="different rows"):
        compare(report, other)


def test_unordered_numeric_validation_checks_every_large_integer_without_boxing(
    monkeypatch,
):
    base = 2**63 + 123
    values = pl.Series(
        "result", [[base, base + 1, base + 1]] * 8200, dtype=pl.List(pl.UInt64)
    )
    # Multiple chunks and a nonzero slice offset must preserve list boundaries.
    left = (
        pl.concat([values.head(4000), values.slice(4000)], rechunk=False)
        .slice(3)
        .to_frame()
    )
    right = left.select(pl.col("result").list.reverse())
    bad = right.with_columns(
        pl.when(pl.int_range(pl.len()) == pl.len() - 1)
        .then(pl.lit([base, base, base + 1], dtype=pl.List(pl.UInt64)))
        .otherwise(pl.col("result"))
        .alias("result")
    )

    def no_boxing(*args, **kwargs):
        raise AssertionError("numeric validation should not box values into Python")

    monkeypatch.setattr(pl.Series, "to_list", no_boxing)
    case = cases(9, 3)["grid_disk"]
    validate(case, left, right)
    with pytest.raises(AssertionError, match="unordered results differ near row 8192"):
        validate(case, left, bad)


@pytest.mark.parametrize(
    "dtype,rows",
    [
        (pl.List(pl.UInt64), [[1, None, 2], None, [], [3], [5, 5, 6, 7]]),
        (pl.List(pl.String), [["a", "b"], [], None, ["c", None, "c"]]),
    ],
)
def test_unordered_validation_preserves_ragged_nulls_and_duplicates(dtype, rows):
    case = cases(9, 3)["grid_disk"]
    left = pl.DataFrame({"result": pl.Series(rows, dtype=dtype)})
    right = left.select(pl.col("result").list.reverse())
    validate(case, left, right)
    changed = list(rows)
    changed[0] = []
    with pytest.raises(AssertionError):
        validate(case, left, pl.DataFrame({"result": pl.Series(changed, dtype=dtype)}))
    changed = [([] if row is None else row) for row in rows]
    with pytest.raises(AssertionError):
        validate(case, left, pl.DataFrame({"result": pl.Series(changed, dtype=dtype)}))
