from pathlib import Path

import h3
import polars as pl
from shapely import from_wkb

import polars_h3 as plh3

TRACTS_PATH = (
    Path(__file__).parents[1]
    / "notebooks"
    / "data"
    / "houston-population-tracts-2020.geoparquet"
)
HARD_TRACTS_PATH = (
    Path(__file__).parent / "data" / "us-census-tracts-hard.geoparquet"
)
HARD_TRACT_IDS = {
    "02016000100",  # Antimeridian-crossing, 28-part Alaska MultiPolygon.
    "06083990000",  # MultiPolygon containing interior rings.
    "15003981200",  # Dispersed Hawaii islands.
    "23025965302",  # Polygon with more than 33,000 coordinates.
    "53055990100",  # Polygon with 18 interior rings.
    "53057990100",  # MultiPolygon with 22 interior rings.
}


def test_houston_census_tract_wkb_matches_python_h3():
    resolution = 8
    tracts = pl.read_parquet(TRACTS_PATH, columns=["geoid", "geometry"])
    covered = tracts.with_columns(cells=plh3.polygon_to_cells("geometry", resolution))

    assert covered.height == 1_421

    for geoid, geometry, actual_cells in covered.iter_rows():
        expected_cells = {
            h3.str_to_int(cell)
            for cell in h3.geo_to_cells(from_wkb(geometry), resolution)
        }

        assert set(actual_cells) == expected_cells, geoid
        assert len(actual_cells) == len(set(actual_cells)), geoid


def test_hard_census_tract_wkb_matches_python_h3():
    resolution = 5
    tracts = pl.read_parquet(HARD_TRACTS_PATH, columns=["geo_id", "geometry"])
    covered = tracts.with_columns(cells=plh3.polygon_to_cells("geometry", resolution))

    assert set(tracts.get_column("geo_id")) == HARD_TRACT_IDS

    for geo_id, geometry, actual_cells in covered.iter_rows():
        expected_cells = {
            h3.str_to_int(cell)
            for cell in h3.geo_to_cells(from_wkb(geometry), resolution)
        }

        assert set(actual_cells) == expected_cells, geo_id
        assert len(actual_cells) == len(set(actual_cells)), geo_id
