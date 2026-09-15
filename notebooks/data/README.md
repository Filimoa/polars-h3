# Polygon-to-H3 notebook sample data

`rhode-island.geojson` is an example-only extract from the local
`state-outlines-simple.json` dataset used while developing the geometry API.
Its attributes identify the U.S. Census Bureau's 2010 Rhode Island state
geography. The underlying Census cartographic boundary data is public-domain
government data and is simplified for small-scale display; do not use this
sample for precise area, perimeter, or boundary analysis.

Source information:
https://www.census.gov/geographies/mapping-files/2010/geo/carto-boundary-file.html

## Houston geometry sample data

`houston-population-tracts-2020.geoparquet` is the compact, offline-ready
sample dataset used by `notebooks/polygon-to-h3.ipynb`. The companion
`houston-ksi-crashes-2024.parquet` extract is retained as optional point data
for readers who want to extend the crosswalk example with `latlng_to_cell`.

- The tract file contains 1,421 Houston-area 2020 census tracts,
  WGS84 WKB geometry, selected demographic measures, and GeoParquet metadata.
- The crash file contains 3,357 records from 2024 whose severity is
  `serious-injury` or `fatal`, with the point coordinates and selected crash
  attributes needed by the walkthrough.

The extracts are tutorial inputs, not authoritative releases. The census
attributes describe 2020 tract estimates while the optional crashes occurred
in 2024. Residential population should not be treated as roadway exposure
without an explicit analytical justification.
