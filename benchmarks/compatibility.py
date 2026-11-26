"""Exact saved-plugin comparisons across encodings, nulls, invalid IDs and slices."""

import argparse
from pathlib import Path

from benchmarks.common import (
    Report,
    configure,
    metadata,
    positive,
    select_cases,
    use_plugin,
)

ID_COLUMNS = {"int_h3_cell", "int_h3_cell_end", "edge", "vertex", "neighbor", "child"}


def variant_frame(frame, encoding):
    import polars as pl

    import polars_h3 as h

    conversions = []
    for column, dtype in frame.schema.items():
        if column in ID_COLUMNS and dtype == pl.UInt64:
            if encoding == "signed":
                conversions.append(pl.col(column).cast(pl.Int64))
            elif encoding == "string":
                conversions.append(
                    pl.Series(
                        column,
                        [
                            format(v, "x") if v is not None else None
                            for v in frame[column]
                        ],
                        dtype=pl.String,
                    )
                )
        elif column == "cell_list" and dtype == pl.List(pl.UInt64):
            if encoding == "signed":
                conversions.append(pl.col(column).cast(pl.List(pl.Int64)))
            elif encoding == "string":
                conversions.append(pl.col(column).list.eval(h.int_to_str(pl.element())))
    frame = frame.with_columns(conversions)
    index = pl.int_range(pl.len())
    replacements = []
    for column, dtype in frame.schema.items():
        value = pl.col(column)
        if column in ID_COLUMNS or column == "str_h3_cell":
            invalid = (
                pl.lit("not-hex") if dtype == pl.String else pl.lit(0, dtype=dtype)
            )
            value = pl.when(index % 17 == 0).then(invalid).otherwise(value)
        replacements.append(
            pl.when(index % 13 == 0).then(None).otherwise(value).alias(column)
        )
    frame = frame.with_columns(replacements)
    # Nonzero, non-byte-aligned validity offset and uneven Arrow chunks.
    return pl.concat([frame[:19], frame[19:32769], frame[32769:]], rechunk=False).slice(
        3
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=positive, default=65540)
    parser.add_argument("--threads", type=positive, default=8)
    parser.add_argument("--functions", nargs="+", default=["all"])
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--plugin-path", type=Path)
    parser.add_argument("--baseline-plugin", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    configure(args, parser)

    from polars.testing import assert_frame_equal

    from benchmarks.internal_workloads import cases, make_data, prepare_frame

    suite = cases()
    names = select_cases(suite, args, parser)
    if not names:
        return
    if not args.baseline_plugin:
        parser.error("--baseline-plugin is required for exact comparisons")
    lengths = sorted({min(n, args.rows) for n in (0, 1, 17, 16385, args.rows)})
    with Report(args.output, metadata(args, "compatibility")) as report:
        use_plugin(args.baseline_plugin)
        data = make_data(args.rows + 3)
        comparisons = 0
        for name in names:
            case = suite[name]
            use_plugin(args.baseline_plugin)
            prepared = prepare_frame(data.head(min(case.rows, len(data))), name)
            for encoding in ("native", "signed", "string"):
                if name == "int_to_str" and encoding == "string":
                    continue  # Public contract requires integer input.
                use_plugin(args.baseline_plugin)
                full = variant_frame(prepared, encoding)
                checked = []
                for rows in lengths:
                    frame = full.head(rows)
                    use_plugin(args.baseline_plugin)
                    expected = frame.select(case.expr().alias("result"))
                    use_plugin(args.plugin_path)
                    actual = frame.select(case.expr().alias("result"))
                    assert_frame_equal(expected, actual, check_exact=True)
                    checked.append(frame.height)
                    comparisons += 1
                report.append(
                    {
                        "name": name,
                        "encoding": encoding,
                        "rows": checked,
                        "status": "complete",
                    }
                )
                print(f"{name} {encoding}: exact match at {checked}", flush=True)
        report.data["comparisons"] = comparisons
        print(f"{comparisons} exact comparisons passed", flush=True)


if __name__ == "__main__":
    main()
