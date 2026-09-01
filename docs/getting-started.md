# Getting started

This page takes you from installation to an H3-indexed Polars dataframe.

## Installation

=== "pip"

    ```bash
    pip install polars-h3
    ```

=== "uv"

    ```bash
    uv add polars-h3
    ```

## Convert coordinates to H3 cells

All public operations return Polars expressions. Pass column names or Polars
expressions, then use the result inside `select`, `with_columns`, or a lazy
query.

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {
        "city": ["San Francisco", "New York"],
        "latitude": [37.7749, 40.7128],
        "longitude": [-122.4194, -74.0060],
    }
)

result = df.with_columns(
    h3_cell=plh3.latlng_to_cell(
        "latitude",
        "longitude",
        resolution=7,
    )
)
```

`result` contains an unsigned 64-bit H3 cell column.

!!! tip "Prefer integer indexes for data pipelines"

    `latlng_to_cell` returns `pl.UInt64` by default. This avoids repeated
    parsing and formatting when you chain multiple H3 operations. Request
    `return_dtype=pl.Utf8` when a human-readable string representation is
    required at a system boundary.

## Compose expressions

H3 expressions can be chained like other Polars expressions:

```python
summary = (
    df.lazy()
    .with_columns(
        h3_cell=plh3.latlng_to_cell(
            "latitude",
            "longitude",
            resolution=7,
        )
    )
    .group_by("h3_cell")
    .agg(locations=pl.len())
    .collect()
)
```

## Next steps

- Read the [user guide](guide.md) for index representations and function
  families.
- Browse the [indexing reference](api-reference/indexing.md) for coordinate and
  boundary operations.
- Use [grid traversal](api-reference/traversal.md) to find nearby cells or
  paths.
- See [graphing](graphing.md) to render cells with Folium.
