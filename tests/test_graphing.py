import struct

import folium
import h3
import polars as pl
import pytest

from polars_h3 import graphing

POLYGON_WKT = (
    "POLYGON((-122.42 37.77,-122.40 37.77,-122.40 37.79,"
    "-122.42 37.79,-122.42 37.77))"
)
POLYGON_WKT_EAST = (
    "POLYGON((-122.40 37.77,-122.38 37.77,-122.38 37.79,"
    "-122.40 37.79,-122.40 37.77))"
)
CELL = h3.str_to_int(h3.latlng_to_cell(37.78, -122.41, 9))
CELL_EAST = h3.str_to_int(h3.latlng_to_cell(37.78, -122.39, 9))


def _polygon_wkb() -> bytes:
    ring = [
        (-122.42, 37.77),
        (-122.40, 37.77),
        (-122.40, 37.79),
        (-122.42, 37.79),
        (-122.42, 37.77),
    ]
    value = bytearray(struct.pack("<BI", 1, 3))
    value.extend(struct.pack("<I", 1))
    value.extend(struct.pack("<I", len(ring)))
    for longitude, latitude in ring:
        value.extend(struct.pack("<dd", longitude, latitude))
    return bytes(value)


def _geojson_layers(map_: folium.Map) -> dict[str, folium.GeoJson]:
    return {
        child.layer_name: child
        for child in map_._children.values()
        if isinstance(child, folium.GeoJson)
    }


def _layer_controls(map_: folium.Map) -> list[folium.LayerControl]:
    return [
        child
        for child in map_._children.values()
        if isinstance(child, folium.LayerControl)
    ]


def test_plot_polygon_coverage_accepts_wkt_and_list_cells():
    coverage = pl.DataFrame(
        {"geometry": [POLYGON_WKT], "cells": [[CELL, CELL_EAST, CELL]]},
        schema={"geometry": pl.String, "cells": pl.List(pl.UInt64)},
    )

    result = graphing.plot_polygon_coverage(
        coverage,
        geometry_col="geometry",
        cells_col="cells",
    )

    layers = _geojson_layers(result)
    assert set(layers) == {"Source geometry", "H3 cells"}
    assert len(layers["Source geometry"].data["features"]) == 1
    cell_features = layers["H3 cells"].data["features"]
    assert len(cell_features) == 2
    assert {feature["properties"]["h3_cell"] for feature in cell_features} == {
        str(CELL),
        str(CELL_EAST),
    }
    for feature in cell_features:
        ring = feature["geometry"]["coordinates"][0]
        assert ring[0] == ring[-1]
    assert len(_layer_controls(result)) == 1


def test_plot_polygon_coverage_accepts_wkb_scalar_cells_and_deduplicates():
    wkb = _polygon_wkb()
    coverage = pl.DataFrame(
        {"geometry": [wkb, wkb], "cell": [CELL, CELL]},
        schema={"geometry": pl.Binary, "cell": pl.UInt64},
    )

    result = graphing.plot_polygon_coverage(
        coverage,
        geometry_col="geometry",
        cells_col="cell",
    )

    layers = _geojson_layers(result)
    assert len(layers["Source geometry"].data["features"]) == 1
    assert len(layers["H3 cells"].data["features"]) == 1


def test_plot_polygon_coverage_supports_multiple_geometries():
    coverage = pl.DataFrame(
        {
            "geometry": [POLYGON_WKT, POLYGON_WKT_EAST],
            "cells": [[CELL], [CELL_EAST]],
        },
        schema={"geometry": pl.String, "cells": pl.List(pl.UInt64)},
    )

    result = graphing.plot_polygon_coverage(
        coverage,
        geometry_col="geometry",
        cells_col="cells",
    )

    layers = _geojson_layers(result)
    assert len(layers["Source geometry"].data["features"]) == 2
    assert len(layers["H3 cells"].data["features"]) == 2


def test_plot_polygon_coverage_renders_geometry_for_empty_coverage():
    coverage = pl.DataFrame({"geometry": [POLYGON_WKT], "cells": [[]]})

    assert coverage.schema["cells"] == pl.List(pl.Null)

    result = graphing.plot_polygon_coverage(
        coverage,
        geometry_col="geometry",
        cells_col="cells",
    )

    assert set(_geojson_layers(result)) == {"Source geometry"}


def test_plot_polygon_coverage_skips_null_rows():
    coverage = pl.DataFrame(
        {"geometry": [POLYGON_WKT, None], "cells": [[CELL], None]},
        schema={"geometry": pl.String, "cells": pl.List(pl.UInt64)},
    )

    result = graphing.plot_polygon_coverage(
        coverage,
        geometry_col="geometry",
        cells_col="cells",
    )

    layers = _geojson_layers(result)
    assert len(layers["Source geometry"].data["features"]) == 1
    assert len(layers["H3 cells"].data["features"]) == 1


def test_plot_polygon_coverage_renders_geometry_for_all_null_cells():
    coverage = pl.DataFrame(
        {"geometry": [POLYGON_WKT], "cell": [None]},
        schema={"geometry": pl.String, "cell": pl.UInt64},
    )

    result = graphing.plot_polygon_coverage(
        coverage,
        geometry_col="geometry",
        cells_col="cell",
    )

    assert set(_geojson_layers(result)) == {"Source geometry"}


def test_plot_polygon_coverage_uses_existing_map_and_layer_control():
    coverage = pl.DataFrame(
        {"geometry": [POLYGON_WKT], "cells": [[CELL]]},
        schema={"geometry": pl.String, "cells": pl.List(pl.UInt64)},
    )
    base_map = folium.Map()
    folium.LayerControl().add_to(base_map)

    result = graphing.plot_polygon_coverage(
        coverage,
        geometry_col="geometry",
        cells_col="cells",
        map=base_map,
    )

    assert result is base_map
    assert len(_layer_controls(result)) == 1


@pytest.mark.parametrize(
    "coverage",
    [
        pl.DataFrame({"geometry": [POLYGON_WKT]}),
        pl.DataFrame(
            {"geometry": [POLYGON_WKT], "cells": [[1]]},
            schema={"geometry": pl.String, "cells": pl.List(pl.UInt64)},
        ),
    ],
    ids=["missing-cells-column", "invalid-cell"],
)
def test_plot_polygon_coverage_validation_does_not_mutate_existing_map(
    coverage: pl.DataFrame,
):
    base_map = folium.Map()
    children_before = tuple(base_map._children)

    with pytest.raises((ValueError, pl.exceptions.ComputeError)):
        graphing.plot_polygon_coverage(
            coverage,
            geometry_col="geometry",
            cells_col="cells",
            map=base_map,
        )

    assert tuple(base_map._children) == children_before


@pytest.mark.parametrize("missing_col", ["geometry", "cells"])
def test_plot_polygon_coverage_requires_columns(missing_col: str):
    coverage = pl.DataFrame(
        {"geometry": [POLYGON_WKT], "cells": [[CELL]]},
        schema={"geometry": pl.String, "cells": pl.List(pl.UInt64)},
    ).drop(missing_col)

    with pytest.raises(ValueError, match="not found"):
        graphing.plot_polygon_coverage(
            coverage,
            geometry_col="geometry",
            cells_col="cells",
        )


def test_plot_polygon_coverage_rejects_all_null_geometry():
    coverage = pl.DataFrame({"geometry": [None], "cells": [[CELL]]})

    assert coverage.schema["geometry"] == pl.Null

    with pytest.raises(ValueError, match="no geometries"):
        graphing.plot_polygon_coverage(
            coverage,
            geometry_col="geometry",
            cells_col="cells",
        )


def test_plot_polygon_coverage_rejects_invalid_geometry():
    coverage = pl.DataFrame(
        {"geometry": ["not wkt"], "cells": [[CELL]]},
        schema={"geometry": pl.String, "cells": pl.List(pl.UInt64)},
    )

    with pytest.raises(pl.exceptions.ComputeError, match="Invalid WKT geometry"):
        graphing.plot_polygon_coverage(
            coverage,
            geometry_col="geometry",
            cells_col="cells",
        )


def test_plot_polygon_coverage_rejects_out_of_range_coordinates():
    coverage = pl.DataFrame(
        {
            "geometry": ["POLYGON((0 91,1 91,1 92,0 92,0 91))"],
            "cells": [[CELL]],
        },
        schema={"geometry": pl.String, "cells": pl.List(pl.UInt64)},
    )

    with pytest.raises(pl.exceptions.ComputeError, match="Invalid polygon coordinate"):
        graphing.plot_polygon_coverage(
            coverage,
            geometry_col="geometry",
            cells_col="cells",
        )


@pytest.mark.parametrize("geometry", ["POLYGON EMPTY", "MULTIPOLYGON EMPTY"])
def test_plot_polygon_coverage_rejects_empty_geometry_with_targeted_error(
    geometry: str,
):
    coverage = pl.DataFrame(
        {"geometry": [geometry], "cells": [[]]},
        schema={"geometry": pl.String, "cells": pl.List(pl.UInt64)},
    )

    with pytest.raises(ValueError, match="no non-empty geometries"):
        graphing.plot_polygon_coverage(
            coverage,
            geometry_col="geometry",
            cells_col="cells",
        )


def test_plot_polygon_coverage_removes_empty_multipolygon_members():
    geometry = "MULTIPOLYGON(EMPTY,((-122.42 37.77,-122.40 37.77,-122.40 37.79,-122.42 37.79,-122.42 37.77)))"
    coverage = pl.DataFrame(
        {"geometry": [geometry], "cells": [[CELL]]},
        schema={"geometry": pl.String, "cells": pl.List(pl.UInt64)},
    )

    result = graphing.plot_polygon_coverage(
        coverage,
        geometry_col="geometry",
        cells_col="cells",
    )

    source = _geojson_layers(result)["Source geometry"].data["features"][0]
    coordinates = source["geometry"]["coordinates"]
    assert len(coordinates) == 1
    assert coordinates[0][0]


def test_plot_polygon_coverage_rejects_invalid_cells():
    coverage = pl.DataFrame(
        {"geometry": [POLYGON_WKT], "cells": [[1]]},
        schema={"geometry": pl.String, "cells": pl.List(pl.UInt64)},
    )

    with pytest.raises(ValueError, match="invalid H3 cell"):
        graphing.plot_polygon_coverage(
            coverage,
            geometry_col="geometry",
            cells_col="cells",
        )


def test_plot_polygon_coverage_rejects_non_geometry_dtype():
    coverage = pl.DataFrame({"geometry": [1], "cells": [[CELL]]})

    with pytest.raises(ValueError, match="WKT String or WKB Binary"):
        graphing.plot_polygon_coverage(
            coverage,
            geometry_col="geometry",
            cells_col="cells",
        )


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"cell_fill_opacity": 1.1}, "cell_fill_opacity"),
        ({"map_size": "tiny"}, "map_size"),
    ],
)
def test_plot_polygon_coverage_validates_options(kwargs: dict, error: str):
    coverage = pl.DataFrame(
        {"geometry": [POLYGON_WKT], "cells": [[CELL]]},
        schema={"geometry": pl.String, "cells": pl.List(pl.UInt64)},
    )

    with pytest.raises(ValueError, match=error):
        graphing.plot_polygon_coverage(
            coverage,
            geometry_col="geometry",
            cells_col="cells",
            **kwargs,
        )
