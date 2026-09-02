from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl
from polars.plugins import register_plugin_function

from .utils import HexResolution, assert_valid_resolution

if TYPE_CHECKING:
    from polars_h3.typing import IntoExprColumn


LIB = Path(__file__).parent.parent


def _polygon_to_geojson(geometry: IntoExprColumn) -> pl.Expr:
    """Convert WKT or WKB polygons to GeoJSON for internal visualization use."""
    return register_plugin_function(
        args=[geometry],
        plugin_path=LIB,
        function_name="polygon_to_geojson",
        is_elementwise=True,
    )


def polygon_to_cells(
    geometry: IntoExprColumn,
    resolution: HexResolution,
) -> pl.Expr:
    """Convert WKT, WKB, or PostGIS EWKB polygons into lists of H3 cells.

    String inputs are parsed as WKT and Binary inputs are parsed as WKB or EWKB.
    Each non-null value must contain a polygon or multipolygon whose coordinates
    use longitude/latitude order. Explicit EWKB SRIDs must be 4326. Cells are
    selected when their centroids lie inside the geometry. Polygon holes and
    antimeridian crossings are supported.

    Parameters
    ----------
    geometry
        String WKT or Binary WKB column or expression.
    resolution
        H3 resolution from 0 through 15.

    Returns
    -------
    pl.Expr
        Expression with dtype ``pl.List(pl.UInt64)``.

    Raises
    ------
    ValueError
        If ``resolution`` is outside the H3 range.
    polars.exceptions.ComputeError
        If a non-null value is malformed WKT/WKB, is not a polygon geometry,
        or contains invalid coordinates.
    """
    assert_valid_resolution(resolution)
    return register_plugin_function(
        args=[geometry],
        plugin_path=LIB,
        function_name="polygon_to_cells",
        is_elementwise=True,
        kwargs={"resolution": resolution},
    )


def polygon_wkt_to_cells(
    wkt: IntoExprColumn,
    resolution: HexResolution,
) -> pl.Expr:
    """Convert WKT polygons into H3 cells.

    This compatibility wrapper delegates to :func:`polygon_to_cells`. New code
    should prefer ``polygon_to_cells``, which also accepts WKB Binary columns.
    """
    return polygon_to_cells(wkt, resolution)


def cells_to_multi_polygon_wkt(cells: IntoExprColumn) -> pl.Expr:
    """Dissolve lists of H3 cells into multipolygon WKT strings.

    Each input row must be a list of unique cells at one resolution. Cell list
    elements may be unsigned integers, signed integers, or hexadecimal strings.
    The returned WKT uses longitude/latitude coordinate order.

    Parameters
    ----------
    cells
        List column or expression containing H3 cells.

    Returns
    -------
    pl.Expr
        String expression containing one ``MULTIPOLYGON`` WKT value per row.

    Raises
    ------
    polars.exceptions.ComputeError
        If the input is not a list, contains invalid or duplicate cells, or
        mixes cell resolutions.
    """
    return register_plugin_function(
        args=[cells],
        plugin_path=LIB,
        function_name="cells_to_multi_polygon_wkt",
        is_elementwise=True,
    )
