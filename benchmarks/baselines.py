"""Optional, time-bounded native-output baselines for Python H3 and h3pandas.

Preloaded inputs and string H3 IDs in every engine. Times computation and native
result construction; input preparation and validation conversion are excluded.
Each case runs in a subprocess so a slow call can actually be stopped.
"""

import argparse
import json
import math
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from benchmarks.common import (
    Report,
    add_controls,
    collect_samples,
    configure,
    measure,
    metadata,
    positive,
    select_cases,
    summarize,
    use_plugin,
)
from benchmarks.workloads import Case, make_frame, validate

FUNCTIONS = (
    "latlng_to_cell",
    "cell_to_parent",
    "get_resolution",
    "is_valid_cell",
    "grid_disk",
    "grid_ring",
)


def seconds(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("seconds must be finite and positive")
    return number


def case_for(name, args):
    import polars as pl

    import polars_h3 as h

    if name == "latlng_to_cell":
        return Case(
            name,
            ("lat", "lng"),
            lambda: h.latlng_to_cell(
                "lat", "lng", args.resolution, return_dtype=pl.String
            ),
            "",
        )
    extra = {
        "cell_to_parent": (args.resolution - 1,),
        "grid_disk": (args.radius,),
        "grid_ring": (args.radius,),
    }.get(name, ())
    expanding = name in ("grid_disk", "grid_ring")
    return Case(
        name,
        ("text",),
        lambda: getattr(h, name)("text", *extra),
        "",
        "list" if expanding else "scalar",
        unordered=expanding,
    )


def run_case(name, args):
    import h3pandas  # noqa: F401 -- registers the pandas accessor
    import pandas as pd
    import polars as pl
    from h3.api import basic_str as h

    use_plugin(args.plugin_path)
    case = case_for(name, args)
    rows = min(args.rows, args.list_rows) if case.category == "list" else args.rows
    frame, generation = measure(
        lambda: make_frame(case, rows, args.resolution, "contiguous", 0)
    )
    expr = case.expression().alias("result")
    reference = frame.select(expr)
    python_input, python_setup = measure(frame.rows)
    function = getattr(h, name)
    extra = {
        "latlng_to_cell": (args.resolution,),
        "cell_to_parent": (args.resolution - 1,),
        "grid_disk": (args.radius,),
        "grid_ring": (args.radius,),
    }.get(name, ())
    if name == "latlng_to_cell":
        pandas_input, pandas_setup = measure(
            lambda: pd.DataFrame(frame.to_dict(as_series=False))
        )
        method, keywords, column = (
            "geo_to_h3",
            {"resolution": args.resolution, "set_index": False},
            f"h3_{args.resolution:02}",
        )
    else:
        pandas_input, pandas_setup = measure(
            lambda: pd.DataFrame(index=pd.Index(frame["text"].to_list()))
        )
        method, keywords, column = {
            "cell_to_parent": (
                "h3_to_parent",
                {"resolution": args.resolution - 1},
                f"h3_{args.resolution - 1:02}",
            ),
            "get_resolution": ("h3_get_resolution", {}, "h3_resolution"),
            "is_valid_cell": ("h3_is_valid", {}, "h3_is_valid"),
            "grid_disk": ("k_ring", {"k": args.radius, "explode": False}, "h3_k_ring"),
            "grid_ring": (
                "hex_ring",
                {"k": args.radius, "explode": False},
                "h3_hex_ring",
            ),
        }[name]
    pandas_call = getattr(pandas_input.h3, method)
    runners = {
        "polars": lambda: frame.select(expr),
        "h3_py": lambda: [function(*row, *extra) for row in python_input],
        "h3pandas": lambda: pandas_call(**keywords)[column],
    }

    def materialize(engine, output):
        if engine == "polars":
            return output
        values = output.to_list() if engine == "h3pandas" else output
        return pl.DataFrame(
            {"result": pl.Series(values, dtype=reference.schema["result"])}
        )

    samples = collect_samples(
        runners,
        args,
        lambda output: validate(case, reference, output),
        materialize=materialize,
    )
    return {
        "name": name,
        "status": "complete",
        "rows": frame.height,
        "representation": "string H3 IDs for all engines",
        "input_schema": {key: str(value) for key, value in frame.schema.items()},
        "setup": {
            "generation": generation,
            "python_inputs": python_setup,
            "pandas_inputs": pandas_setup,
        },
        "validation": "every output, all rows; only unordered cell lists and integer widths normalized",
        "results": summarize(samples, "native-output"),
    }


def run_worker(command, timeout):
    """subprocess.run kills and waits for the child on TimeoutExpired."""
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return False
    if result.returncode:
        raise RuntimeError(
            f"benchmark worker failed (exit {result.returncode}):\n{result.stderr[-6000:]}"
        )
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_controls(parser, rows=10_000)
    parser.set_defaults(warmups=1, iterations=3)
    parser.add_argument("--list-rows", type=positive, default=1_000)
    parser.add_argument("--resolution", type=int, choices=range(2, 15), default=9)
    parser.add_argument("--radius", type=positive, default=3)
    parser.add_argument("--seconds-per-case", type=seconds, default=10.0)
    parser.add_argument("--budget-seconds", type=seconds, default=60.0)
    parser.add_argument("--_worker", choices=FUNCTIONS, help=argparse.SUPPRESS)
    args = parser.parse_args()
    configure(args, parser)
    if args.baseline_plugin:
        parser.error("use internal or DuckDB for saved-plugin baseline comparisons")
    names = select_cases(dict.fromkeys(FUNCTIONS), args, parser)
    if not names:
        return
    if args._worker:
        with args.output.open("x") as stream:
            json.dump(run_case(args._worker, args), stream)
        return

    info = metadata(args, "baselines", ("h3", "pandas", "h3pandas"))
    info["timing_contracts"] = {"native-output": __doc__}
    info["python_h3_api"] = "h3.api.basic_str"
    info["budget_contract"] = (
        "Case subprocess deadlines include startup, setup, warmups, timing and validation. Total budget covers sequential workers; parent metadata/report I/O is additional. Timed-out cases publish no partial samples."
    )
    deadline = time.monotonic() + args.budget_seconds
    with (
        Report(args.output, info) as report,
        tempfile.TemporaryDirectory(prefix="h3-baselines-") as directory,
    ):
        for name in names:
            remaining = deadline - time.monotonic()
            rows = (
                min(args.rows, args.list_rows)
                if name in ("grid_disk", "grid_ring")
                else args.rows
            )
            if remaining <= 0:
                report.append(
                    {
                        "name": name,
                        "rows": rows,
                        "status": "skipped",
                        "reason": "suite budget exhausted",
                        "results": [],
                    }
                )
                print(f"{name}: skipped (suite budget exhausted)", flush=True)
                continue
            timeout = min(remaining, args.seconds_per_case)
            output = Path(directory) / f"{name}.json"
            command = [
                sys.executable,
                "-m",
                "benchmarks.baselines",
                "--_worker",
                name,
                "--output",
                str(output),
            ]
            for option in (
                "rows",
                "list_rows",
                "threads",
                "iterations",
                "warmups",
                "resolution",
                "radius",
            ):
                command.extend(
                    ["--" + option.replace("_", "-"), str(getattr(args, option))]
                )
            if args.plugin_path:
                command.extend(["--plugin-path", str(args.plugin_path)])
            if not run_worker(command, timeout):
                report.append(
                    {
                        "name": name,
                        "rows": rows,
                        "status": "timed_out",
                        "reason": "case or remaining suite budget exceeded",
                        "limit_seconds": timeout,
                        "results": [],
                    }
                )
                print(
                    f"{name}: timed out after {timeout:.2f}s; no timing reported",
                    flush=True,
                )
                continue
            case = json.loads(output.read_text())
            report.append(case)
            times = " ".join(
                f"{r['engine']}={r['median_seconds']:.6f}s" for r in case["results"]
            )
            medians = {
                result["engine"]: result["median_seconds"] for result in case["results"]
            }
            ratios = " ".join(
                f"{engine}/polars={medians[engine] / medians['polars']:.2f}x"
                for engine in ("h3_py", "h3pandas")
            )
            print(f"{name:24} {case['rows']:>8,} rows {times} {ratios}", flush=True)
    if report.data["status"] == "partial":
        print(
            "Partial run: one or more cases exceeded the budget. Increase limits explicitly to retry.",
            flush=True,
        )


if __name__ == "__main__":
    main()
