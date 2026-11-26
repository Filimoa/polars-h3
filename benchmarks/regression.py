"""Broad internal timings, optionally paired with an immutable baseline plugin.

With a baseline, every output must match exact values, dtypes and list order.
Without one, validation checks repeatability only, not independent correctness.
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_controls(parser)
    args = parser.parse_args()
    configure(args, parser)

    from polars.testing import assert_frame_equal

    from benchmarks.internal_workloads import cases, make_data, prepare_frame

    suite = cases()
    names = select_cases(suite, args, parser)
    if not names:
        return
    use_plugin(args.plugin_path)
    info = metadata(args, "internal")
    info["timing_contracts"] = {
        "resident": "Preloaded Polars inputs; select and full DataFrame materialization. Setup and exact validation excluded."
    }
    info["validation"] = (
        "exact baseline comparison"
        if args.baseline_plugin
        else "current-build repeatability only; no independent correctness oracle"
    )
    with Report(args.output, info) as report:
        data, generation = measure(
            lambda: make_data(
                min(args.rows, max(suite[name].rows for name in names))
            ).rechunk()
        )
        report.data["setup"] = {"generation": generation}
        for name in names:
            case = suite[name]
            use_plugin(args.plugin_path)
            frame, preparation = measure(
                lambda case=case, name=name: prepare_frame(
                    data.head(min(args.rows, case.rows)), name
                ).rechunk()
            )
            expressions = {}
            if args.baseline_plugin:
                use_plugin(args.baseline_plugin)
                expressions["baseline"] = case.expr().alias("result")
            use_plugin(args.plugin_path)
            expressions["polars"] = case.expr().alias("result")
            reference = frame.select(expressions.get("baseline", expressions["polars"]))
            runners = {
                engine: (lambda expr=expr, frame=frame: frame.select(expr))
                for engine, expr in expressions.items()
            }
            samples = collect_samples(
                runners,
                args,
                lambda output, reference=reference: assert_frame_equal(
                    reference, output, check_exact=True
                ),
            )
            results = summarize(samples, "resident")
            report.append(
                {
                    "name": name,
                    "rows": frame.height,
                    "output_rows": reference.height,
                    "input_schema": {
                        key: str(value) for key, value in frame.schema.items()
                    },
                    "input_chunks": frame.n_chunks(),
                    "input_bytes": frame.estimated_size(),
                    "output_bytes": reference.estimated_size(),
                    "setup": {"preparation": preparation},
                    "validation": info["validation"],
                    "results": results,
                }
            )
            times = " ".join(
                f"{r['engine']}={r['median_seconds']:.6f}s" for r in results
            )
            print(f"{name:28} {frame.height:>9,} rows {times}", flush=True)


if __name__ == "__main__":
    main()
