# H3 expressions for Polars

Polars H3 brings fast, Polars-native [H3](https://h3geo.org/) indexing,
inspection, traversal, hierarchy, edge, vertex, and metric operations to your
dataframes.

[Get started](getting-started.md){ .md-button .md-button--primary }
[Browse the API](api-reference/index.md){ .md-button }

```python
import polars as pl
import polars_h3 as plh3

df = pl.DataFrame(
    {
        "latitude": [37.7749],
        "longitude": [-122.4194],
    }
).with_columns(
    h3_cell=plh3.latlng_to_cell(
        "latitude",
        "longitude",
        resolution=7,
    )
)
```

## Why Polars H3?

- **Polars-native expressions.** Compose H3 operations inside `select`,
  `with_columns`, lazy queries, and the rest of the Polars expression API.
- **Rust-backed execution.** H3 operations run in the Polars plugin engine
  without Python-level row loops.
- **Flexible cell representations.** Use `UInt64`, `Int64`, or string H3
  indexes where supported. Prefer `UInt64` in performance-sensitive pipelines.
- **Focused H3 coverage.** Work with cells, hierarchy, traversal, directed
  edges, vertices, and metrics. Polygon-to-cell geometry operations are outside
  the package's scope.

## Find what you need

| If you want to… | Start here |
| --- | --- |
| Install the package and run a first query | [Getting started](getting-started.md) |
| Understand expressions, index types, and function families | [User guide](guide.md) |
| Look up a function signature or return type | [API reference](api-reference/index.md) |
| Draw cells on an interactive map | [Graphing](graphing.md) |

Polars H3 is powered by [h3o](https://github.com/HydroniumLabs/h3o) and built
for the [Polars](https://pola.rs/) ecosystem.
