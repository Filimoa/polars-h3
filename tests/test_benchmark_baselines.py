"""Bounded slow-library comparisons must stay fair and actually stop workers."""

import json
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

from benchmarks.baselines import FUNCTIONS, run_case, run_worker
from benchmarks.common import Report
from benchmarks.compare_results import compare


@pytest.mark.parametrize("name", FUNCTIONS)
def test_baselines_validate_identical_inputs_and_full_outputs(name):
    pytest.importorskip("h3pandas")
    args = SimpleNamespace(
        rows=8,
        list_rows=4,
        resolution=9,
        radius=3,
        plugin_path=None,
        warmups=1,
        iterations=2,
    )
    result = run_case(name, args)
    assert result["status"] == "complete"
    assert result["rows"] == (4 if name in ("grid_disk", "grid_ring") else 8)
    assert {record["engine"] for record in result["results"]} == {
        "polars",
        "h3_py",
        "h3pandas",
    }
    assert all(len(record["runs"]) == 2 for record in result["results"])
    assert result["representation"] == "string H3 IDs for all engines"


def test_timeout_terminates_the_worker():
    start = time.monotonic()
    assert not run_worker([sys.executable, "-c", "import time; time.sleep(10)"], 0.05)
    assert time.monotonic() - start < 3
    assert run_worker([sys.executable, "-c", "pass"], 3)
    with pytest.raises(RuntimeError, match="exit 1"):
        run_worker([sys.executable, "-c", "raise ValueError('invalid results')"], 3)


def test_partial_reports_cannot_be_compared(tmp_path):
    output = tmp_path / "partial.json"
    with Report(output, {"suite": "baselines"}) as report:
        report.append({"name": "grid_disk", "status": "timed_out", "results": []})
    saved = json.loads(output.read_text())
    assert saved["status"] == "partial"
    with pytest.raises(ValueError, match="incomplete or failed"):
        compare(saved, saved)


def test_cli_budget_records_timeout_without_performance_claims(tmp_path):
    pytest.importorskip("h3pandas")
    output = tmp_path / "budget.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "benchmarks",
            "baselines",
            "--rows",
            "1000000",
            "--budget-seconds",
            "0.01",
            "--seconds-per-case",
            "0.005",
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    saved = json.loads(output.read_text())
    assert saved["status"] == "partial"
    assert len(saved["cases"]) == len(FUNCTIONS)
    assert all(case["status"] in ("timed_out", "skipped") for case in saved["cases"])
    assert all(case["results"] == [] for case in saved["cases"])
    assert "Partial run" in completed.stdout


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf"])
def test_cli_rejects_invalid_deadlines(value, tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "benchmarks",
            "baselines",
            "--seconds-per-case",
            value,
            "--output",
            str(tmp_path / "invalid.json"),
        ],
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "finite and positive" in completed.stderr
    assert not (tmp_path / "invalid.json").exists()
