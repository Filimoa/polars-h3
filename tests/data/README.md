# Geometry test data

`us-census-tracts-hard.geoparquet` is a six-row extract from the full U.S.
Census tract GeoParquet used during geometry development. It contains WKB
geometries in NAD83 (EPSG:4269) and retains GeoParquet metadata.

The rows were selected as adversarial real-world parser and polygon coverage
cases:

| Census tract GEOID | Stress case |
| --- | --- |
| `02016000100` | Antimeridian-crossing Alaska MultiPolygon with 28 parts |
| `06083990000` | MultiPolygon containing interior rings |
| `15003981200` | Dispersed Hawaii island MultiPolygon |
| `23025965302` | Polygon containing more than 33,000 coordinates |
| `53055990100` | Polygon with 18 interior rings |
| `53057990100` | MultiPolygon with 22 interior rings |

The integration test compares every geometry with the regular Python `h3`
implementation. Keep this extract small and deterministic; the complete
national file is intended for manual stress tests and benchmarks, not CI.
