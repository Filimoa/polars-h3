"""Polars-native expressions versus Python H3 callbacks over identical inputs.

Includes Python dispatch and construction of a one-column Polars result. This
measures an end-to-end Polars workflow, not isolated native H3 kernel latency.
"""

import argparse

from benchmarks.common import (
    Report,
    add_controls,
    collect_samples,
    configure,
    measure,
    metadata,
    select_cases,
    summarize,
    use_plugin,
)
from benchmarks.workloads import Case, make_frame, validate
from benchmarks.workloads import cases as duckdb_cases


def cases(resolution, radius):
    import polars_h3 as h

    names = (
        "latlng_to_cell",
        "cell_to_latlng",
        "get_resolution",
        "int_to_str",
        "str_to_int",
        "is_valid_cell",
        "are_neighbor_cells",
        "cell_to_parent",
        "cell_to_children",
        "grid_disk",
        "grid_ring",
        "grid_distance",
    )
    existing = duckdb_cases(resolution, radius)
    suite = {name: existing[name] for name in names}
    suite["cell_to_boundary"] = Case(
        "cell_to_boundary",
        ("cell",),
        lambda: h.cell_to_boundary("cell"),
        "",
        "list",
        floating=True,
    )
    suite["grid_path_cells"] = Case(
        "grid_path_cells",
        ("cell", "neighbor"),
        lambda: h.grid_path_cells("cell", "neighbor"),
        "",
        "list",
    )
    return suite


def python_expression(case, args, dtype):
    import polars as pl
    from h3.api import basic_int as h

    function = getattr(h, case.name)
    extra = {
        "latlng_to_cell": (args.resolution,),
        "cell_to_parent": (args.resolution - 1,),
        "cell_to_children": (args.resolution + 1,),
        "grid_disk": (args.radius,),
        "grid_ring": (args.radius,),
    }.get(case.name, ())

    def normalize(value):
        # h3-py returns tuples for coordinates; match Polars list representation.
        return (
            [normalize(v) for v in value] if isinstance(value, tuple | list) else value
        )

    def apply(row):
        return normalize(function(*(row[column] for column in case.columns), *extra))

    return (
        pl.struct(case.columns).map_elements(apply, return_dtype=dtype).alias("result")
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_controls(parser, rows=10_000)
    parser.add_argument("--resolution", type=int, choices=range(2, 15), default=9)
    parser.add_argument("--radius", type=int, choices=range(1, 11), default=3)
    args = parser.parse_args()
    configure(args, parser)
    if args.baseline_plugin:
        parser.error("use the internal or DuckDB suite for saved-baseline comparisons")
    suite = cases(args.resolution, args.radius)
    names = select_cases(suite, args, parser)
    if not names:
        return
    use_plugin(args.plugin_path)
    info = metadata(args, "python", ("h3",))
    info["timing_contracts"] = {"python-callback": __doc__}
    info["python_h3_api"] = "h3.api.basic_int"
    with Report(args.output, info) as report:
        for name in names:
            case = suite[name]
            frame, generation = measure(
                lambda case=case: make_frame(
                    case, args.rows, args.resolution, "contiguous", 0
                )
            )
            expr = case.expression().alias("result")
            reference = frame.select(expr)
            python = python_expression(case, args, reference.schema["result"])
            runners = {
                "polars": lambda frame=frame, expr=expr: frame.select(expr),
                "h3_py": lambda frame=frame, python=python: frame.select(python),
            }
            samples = collect_samples(
                runners,
                args,
                lambda output, case=case, reference=reference: validate(
                    case, reference, output
                ),
            )
            results = summarize(samples, "python-callback")
            report.append(
                {
                    "name": name,
                    "rows": frame.height,
                    "input_schema": {
                        key: str(value) for key, value in frame.schema.items()
                    },
                    "input_chunks": frame.n_chunks(),
                    "input_bytes": frame.estimated_size(),
                    "output_bytes": reference.estimated_size(),
                    "setup": {"generation": generation},
                    "validation": "all rows, every output; integer representation, unordered lists sorted, floating tolerance 1e-7 relative/1e-9 absolute",
                    "results": results,
                }
            )
            times = " ".join(
                f"{r['engine']}={r['median_seconds']:.6f}s" for r in results
            )
            print(f"{name:28} {frame.height:>9,} rows {times}", flush=True)


if __name__ == "__main__":
    main()
