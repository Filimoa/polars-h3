"""Validated DuckDB comparison with separate native and Arrow timing contracts."""

import argparse
import random

from benchmarks.common import (
    Report,
    add_controls,
    collect_samples,
    configure,
    measure,
    positive,
    select_cases,
    summarize,
    use_plugin,
)
from benchmarks.common import (
    metadata as base_metadata,
)
from benchmarks.workloads import Case, cases, make_frame, validate


def run_case(case: Case, args, con) -> dict:
    import pyarrow as pa

    rows = {"scalar": args.rows, "list": args.list_rows, "polygon": args.polygon_rows}[
        case.category
    ]
    frame, generation = measure(
        lambda: make_frame(case, rows, args.resolution, args.layout, args.null_every)
    )
    arrow, conversion = measure(frame.to_arrow)
    # Chunked Arrow lets DuckDB distribute batches rather than bottleneck on a
    # single Arrow chunk. Construct the table once; readers are one-shot objects.
    arrow = pa.Table.from_batches(arrow.to_batches(max_chunksize=args.arrow_batch_rows))
    con.register("arrow_input", arrow)
    _, loading = measure(
        lambda: con.execute(
            "CREATE OR REPLACE TEMP TABLE input AS SELECT * FROM arrow_input"
        )
    )
    expr = case.expression().alias("result")
    expressions = {"polars": expr}
    if args.baseline_plugin:
        use_plugin(args.baseline_plugin)
        expressions["baseline"] = case.expression().alias("result")
        use_plugin(args.plugin_path)
    reference = frame.select(expr)
    sql = f"SELECT {case.sql} AS result FROM input"
    validate(case, reference, con.execute(sql).fetch_arrow_table())
    records = []
    for mode in args.modes:
        source = "arrow_input" if mode == "arrow-scan" else "input"
        query = f"SELECT {case.sql} AS result FROM {source}"

        def polars_run(engine, mode=mode):
            result = frame.select(expressions[engine])
            return result if mode == "resident" else result.to_arrow()

        def duckdb_run(mode=mode, query=query):
            if mode in ("resident", "arrow-materialized"):
                con.execute(f"CREATE TEMP TABLE output AS {query}")
                return (
                    None
                    if mode == "resident"
                    else con.execute("SELECT * FROM output").fetch_arrow_table()
                )
            return con.execute(query).fetch_arrow_table()

        runners = {
            engine: (lambda engine=engine: polars_run(engine)) for engine in expressions
        }
        runners["duckdb"] = duckdb_run

        def prepare(engine, mode=mode):
            if engine == "duckdb" and mode in ("resident", "arrow-materialized"):
                con.execute("DROP TABLE IF EXISTS output")

        def materialize(engine, output):
            return (
                con.execute("SELECT * FROM output").fetch_arrow_table()
                if output is None
                else output
            )

        samples = collect_samples(
            runners,
            args,
            lambda output: validate(case, reference, output),
            prepare=prepare,
            materialize=materialize,
        )
        records.extend(summarize(samples, mode))
        current = {
            result["engine"]: result for result in records if result["mode"] == mode
        }
        a, b = current["polars"], current["duckdb"]
        gain = (
            f" before/after={current['baseline']['median_seconds']/a['median_seconds']:.2f}x"
            if "baseline" in current
            else ""
        )
        print(
            f"{case.name:28} {rows:>10,} {mode:12} polars={a['median_seconds']:.5f}s duckdb={b['median_seconds']:.5f}s ratio={b['median_seconds']/a['median_seconds']:.2f}x{gain}",
            flush=True,
        )
    result = {
        "name": case.name,
        "rows": rows,
        "sql": sql,
        "polars_expression": str(expr),
        "input_schema": {name: str(dtype) for name, dtype in frame.schema.items()},
        "input_chunks": frame.n_chunks(),
        "input_bytes": frame.estimated_size(),
        "output_bytes": reference.estimated_size(),
        "output_chunks": reference.n_chunks(),
        "setup": {
            "generation": generation,
            "to_arrow": conversion,
            "duckdb_native_load": loading,
        },
        "validation": "all rows, every output",
        "results": records,
    }
    con.unregister("arrow_input")
    con.execute("DROP TABLE IF EXISTS output")
    con.execute("DROP TABLE input")
    return result


def metadata(args, con):
    result = base_metadata(args, "duckdb", ("duckdb", "pyarrow", "h3"))
    result.update(
        {
            "duckdb_h3": con.execute(
                "SELECT extension_version FROM duckdb_extensions() WHERE extension_name='h3'"
            ).fetchone()[0],
            "h3_core": con.execute("SELECT h3_version()").fetchone()[0],
            "duckdb_threads": con.execute(
                "SELECT current_setting('threads')"
            ).fetchone()[0],
            "timing_contracts": {
                "resident": "Preloaded inputs; Polars select materializes a DataFrame, DuckDB CTAS materializes a temporary native table. No output export. Not pure kernel time: allocators and storage differ.",
                "arrow-materialized": "Preloaded native inputs; Polars select then Arrow export; DuckDB CTAS then SELECT/export of that result, all timed. Materializing before export allows parallel H3 computation in DuckDB.",
                "arrow-output": "Preloaded native inputs, full query execution and Arrow result materialization for both engines.",
                "arrow-scan": "Polars native frame versus DuckDB registered batched Arrow input; both fully materialize Arrow output. Interoperability scenario, not native DuckDB throughput.",
                "setup": "Input generation, Polars-to-Arrow, native DuckDB ingestion timed separately and excluded from query samples.",
            },
        }
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    add_controls(parser, rows=5_000_000)
    parser.add_argument("--list-rows", type=positive, default=250_000)
    parser.add_argument("--polygon-rows", type=positive, default=2_000)
    parser.add_argument("--resolution", type=int, choices=range(2, 15), default=9)
    parser.add_argument("--radius", type=positive, default=3)
    parser.add_argument("--arrow-batch-rows", type=positive, default=65536)
    parser.add_argument(
        "--modes",
        nargs="+",
        choices=["resident", "arrow-materialized", "arrow-output", "arrow-scan"],
        default=["resident", "arrow-materialized"],
    )
    parser.add_argument(
        "--layout", choices=["contiguous", "chunked", "sliced"], default="contiguous"
    )
    parser.add_argument("--null-every", type=int, default=0)
    parser.add_argument("--install-extension", action="store_true")
    args = parser.parse_args()
    if args.null_every < 0:
        parser.error("--null-every cannot be negative")
    configure(args, parser)
    suite = cases(args.resolution, args.radius)
    names = select_cases(suite, args, parser)
    if not names:
        return
    use_plugin(args.plugin_path)
    import duckdb

    con = duckdb.connect(config={"threads": args.threads})
    if args.install_extension:
        con.execute("INSTALL h3 FROM community")
    con.execute("LOAD h3")
    # Fixed shuffle avoids a permanent easy-to-hard order.
    random.Random(42).shuffle(names)
    try:
        with Report(args.output, metadata(args, con)) as report:
            for name in names:
                report.append(run_case(suite[name], args, con))
    finally:
        con.close()


if __name__ == "__main__":
    main()
