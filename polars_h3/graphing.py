import json
from typing import Any, Literal, Union

import polars as pl

from .core.geometry import _polygon_to_geojson
from .core.indexing import cell_to_boundary


def _hex_bounds(
    df: pl.DataFrame, boundary_col: str = "boundary"
) -> tuple[tuple[float, float], tuple[float, float]]:
    df_flat = (
        df.explode(boundary_col)
        .with_columns(
            [
                pl.col(boundary_col).list.get(0).alias("lat"),
                pl.col(boundary_col).list.get(1).alias("lng"),
            ]
        )
        .drop(boundary_col)
    )

    min_lat = float(df_flat["lat"].min())  # type: ignore
    max_lat = float(df_flat["lat"].max())  # type: ignore
    min_lng = float(df_flat["lng"].min())  # type: ignore
    max_lng = float(df_flat["lng"].max())  # type: ignore

    return ((min_lat, min_lng), (max_lat, max_lng))


def _cells_with_boundaries(
    df: pl.DataFrame, cells_col: str, *, require_cells: bool = True
) -> pl.DataFrame:
    if cells_col not in df.schema:
        raise ValueError(f"column {cells_col!r} not found")

    cells = df.select(cells_col).drop_nulls(subset=[cells_col])
    if df.schema[cells_col].base_type() == pl.List:
        cells = cells.explode(cells_col)

    cells = cells.drop_nulls(subset=[cells_col]).unique(
        subset=[cells_col], maintain_order=True
    )
    if cells.height == 0:
        if require_cells:
            raise ValueError("DataFrame contains no cells to plot")
        return cells.with_columns(
            pl.lit(None, dtype=pl.List(pl.List(pl.Float64))).alias("boundary")
        )

    cells = cells.with_columns(cell_to_boundary(pl.col(cells_col)).alias("boundary"))
    if cells.filter(pl.col("boundary").is_null()).height:
        raise ValueError(f"column {cells_col!r} contains an invalid H3 cell")
    return cells


def _geometry_feature_collection(df: pl.DataFrame, geometry_col: str) -> dict[str, Any]:
    if geometry_col not in df.schema:
        raise ValueError(f"column {geometry_col!r} not found")
    if df.schema[geometry_col] not in (pl.String, pl.Binary, pl.Null):
        raise ValueError(
            f"column {geometry_col!r} must contain WKT String or WKB Binary values"
        )

    geometries = (
        df.select(_polygon_to_geojson(geometry_col).alias("geometry"))
        .drop_nulls()
        .unique(maintain_order=True)
        .get_column("geometry")
        .to_list()
    )
    if not geometries:
        raise ValueError("DataFrame contains no geometries to plot")

    features = []
    for geometry in geometries:
        parsed = json.loads(geometry)
        if not parsed["coordinates"]:
            continue
        features.append(
            {
                "type": "Feature",
                "properties": {},
                "geometry": parsed,
            }
        )
    if not features:
        raise ValueError("DataFrame contains no non-empty geometries to plot")

    return {"type": "FeatureCollection", "features": features}


def _cell_feature_collection(cells: pl.DataFrame, cells_col: str) -> dict[str, Any]:
    features = []
    for cell, boundary in cells.iter_rows():
        coordinates = [[longitude, latitude] for latitude, longitude in boundary]
        if coordinates and coordinates[0] != coordinates[-1]:
            coordinates.append(coordinates[0])
        features.append(
            {
                "type": "Feature",
                "properties": {"h3_cell": str(cell)},
                "geometry": {"type": "Polygon", "coordinates": [coordinates]},
            }
        )
    return {"type": "FeatureCollection", "features": features}


def _combine_bounds(*bounds: Any) -> tuple[tuple[float, float], tuple[float, float]]:
    valid_bounds = []
    for bound in bounds:
        south, west = bound[0]
        north, east = bound[1]
        if (
            south is not None
            and west is not None
            and north is not None
            and east is not None
        ):
            valid_bounds.append(((south, west), (north, east)))

    if not valid_bounds:
        raise ValueError("Cannot determine map bounds")
    return (
        (
            min(bound[0][0] for bound in valid_bounds),
            min(bound[0][1] for bound in valid_bounds),
        ),
        (
            max(bound[1][0] for bound in valid_bounds),
            max(bound[1][1] for bound in valid_bounds),
        ),
    )


def plot_polygon_coverage(
    df: pl.DataFrame,
    *,
    geometry_col: str,
    cells_col: str,
    map: Union[Any, None] = None,
    cell_color: str = "#2563eb",
    cell_fill_opacity: float = 0.2,
    geometry_color: str = "#dc2626",
    map_size: Literal["medium", "large"] = "large",
) -> Any:
    """Plot H3 polygon coverage over its source geometry on a Folium map.

    ``geometry_col`` accepts WKT String or WKB/EWKB Binary polygons, matching
    :func:`polars_h3.polygon_to_cells`. ``cells_col`` may contain one H3 cell
    per row or a List of cells. Repeated geometries and cells are rendered
    once. Null values are skipped, and valid geometries with empty coverages
    are still displayed.

    Folium is an optional dependency. Install it with ``pip install folium``.
    Input geometry coordinates must use WGS84 longitude/latitude order.
    """
    if df.height == 0:
        raise ValueError("DataFrame is empty")
    if not 0.0 <= cell_fill_opacity <= 1.0:
        raise ValueError("cell_fill_opacity must be between 0 and 1")
    if map_size not in ("medium", "large"):
        raise ValueError("map_size must be 'medium' or 'large'")

    try:
        import folium
    except ImportError as e:
        raise ImportError(
            "folium is required to plot polygon coverage. "
            "Install with `pip install folium`"
        ) from e

    geometry_features = _geometry_feature_collection(df, geometry_col)
    cells = _cells_with_boundaries(df, cells_col, require_cells=False)
    geometry_layer = folium.GeoJson(
        geometry_features,
        name="Source geometry",
        style_function=lambda _: {
            "color": geometry_color,
            "weight": 3,
            "fillOpacity": 0,
        },
    )

    cell_layer = None
    if cells.height:
        cell_layer = folium.GeoJson(
            _cell_feature_collection(cells, cells_col),
            name="H3 cells",
            style_function=lambda _: {
                "color": cell_color,
                "weight": 1,
                "fillColor": cell_color,
                "fillOpacity": cell_fill_opacity,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["h3_cell"],
                aliases=["H3 cell:"],
            ),
        )

    if map is None:
        map = folium.Map(
            zoom_start=8,
            tiles="cartodbpositron",
            width="50%" if map_size == "medium" else "100%",
            height="50%" if map_size == "medium" else "100%",
        )

    geometry_layer.add_to(map)
    layers = [geometry_layer.get_bounds()]
    if cell_layer is not None:
        cell_layer.add_to(map)
        layers.append(cell_layer.get_bounds())

    map.fit_bounds(_combine_bounds(*layers))
    if not any(
        isinstance(child, folium.LayerControl) for child in map._children.values()
    ):
        folium.LayerControl().add_to(map)
    return map


def plot_hex_outlines(
    df: pl.DataFrame,
    *,
    hex_id_col: str,
    map: Union[Any, None] = None,
    outline_color: str = "red",
    map_size: Literal["medium", "large"] = "medium",
) -> Any:
    """
    Plot hexagon outlines on a Folium map.

    Parameters
    ----------
    df : pl.DataFrame
        A DataFrame that must contain a column of hex IDs.
    hex_id_col : str
        The name of the column in `df` that contains hexagon identifiers (H3 cell IDs).
    map : folium.Map or None, optional
        An existing Folium map object on which to plot. If None, a new map is created.
    outline_color : str, optional
        The color used to outline the hexagons. Defaults to "red".
    map_size : {"medium", "large"}, optional
        The size of the displayed map. "medium" fits a 50% view, "large" takes 100%. Defaults to "medium".

    Returns
    -------
    folium.Map
        A Folium map object with hexagon outlines added.

    Raises
    ------
    ValueError
        If the input DataFrame is empty.
    ImportError
        If Folium is not installed.
    """
    if df.height == 0:
        raise ValueError("DataFrame is empty")

    try:
        import folium
    except ImportError as e:
        raise ImportError(
            "folium is required to plot hex outlines. Install with `pip install folium`"
        ) from e

    if not map:
        map = folium.Map(
            zoom_start=13,
            tiles="cartodbpositron",
            width="50%" if map_size == "medium" else "100%",
            height="50%" if map_size == "medium" else "100%",
        )

    df = (
        df.drop_nulls(subset=[hex_id_col])
        .with_columns(
            [
                cell_to_boundary(pl.col(hex_id_col)).alias("boundary"),
            ]
        )
        .filter(pl.col("boundary").is_not_null())
    )

    for hex_cord in df["boundary"].to_list():
        folium.Polygon(locations=hex_cord, weight=5, color=outline_color).add_to(map)

    map_bounds = _hex_bounds(df, "boundary")
    map.fit_bounds(map_bounds)
    return map


def plot_hex_fills(
    df: pl.DataFrame,
    *,
    hex_id_col: str,
    metric_col: str,
    map: Union[Any, None] = None,
    map_size: Literal["medium", "large"] = "medium",
) -> Any:
    """
    Render filled hexagonal cells on a Folium map, colorized by a specified metric.

    If no map is provided, a new Folium map is created. The map is automatically
    fit to the bounds of the plotted polygons.

    #### Parameters
    - `df`: pl.DataFrame
    - `hex_id_col`: str
      Column name in `df` holding H3 cell indices.
    - `metric_col`: str
      Column name in `df` containing the metric values for colorization.
    - `map`: folium.Map | None, default None
      An existing Folium Map object. If None, a new map is created.
    - `map_size`: Literal["medium", "large"], default "medium"
      Controls the size of the Folium map. `"medium"` sets width/height to 50% while `"large"` sets it to 100%.

    #### Returns
    folium.Map
      The Folium Map object with the rendered hexagon polygons.
    """
    if df.height == 0:
        raise ValueError("DataFrame is empty")

    try:
        import folium
        import matplotlib
    except ImportError as e:
        raise ImportError(
            "folium and matplotlib are required to plot hex fills. Install with `pip install folium matplotlib`"
        ) from e

    if not map:
        map = folium.Map(
            zoom_start=13,
            tiles="cartodbpositron",
            width="50%" if map_size == "medium" else "100%",
            height="50%" if map_size == "medium" else "100%",
        )

    df = (
        df.drop_nulls(subset=[hex_id_col, metric_col])
        .with_columns(
            [
                cell_to_boundary(pl.col(hex_id_col)).alias("boundary"),
                pl.col(metric_col).log1p().alias("normalized_metric"),
            ]
        )
        .filter(pl.col("boundary").is_not_null())
    )

    hexagons = df[hex_id_col].to_list()
    metrics = df[metric_col].to_list()
    compressed_metrics = df["normalized_metric"].to_list()
    boundaries = df["boundary"].to_list()

    min_val = min(compressed_metrics)
    max_val = max(compressed_metrics)

    if max_val == min_val:
        normalized_metrics = [0.0] * len(compressed_metrics)
    else:
        normalized_metrics = [
            (x - min_val) / (max_val - min_val) for x in compressed_metrics
        ]

    colormap = matplotlib.colormaps.get_cmap("plasma")

    for (hexagon, metric, boundary), norm_metric in zip(
        zip(hexagons, metrics, boundaries), normalized_metrics, strict=False
    ):
        rgba = colormap(norm_metric)
        color = (
            f"#{int(rgba[0] * 255):02x}{int(rgba[1] * 255):02x}{int(rgba[2] * 255):02x}"
        )

        folium.Polygon(
            locations=boundary,
            fill=True,
            fill_opacity=0.6 + 0.4 * norm_metric,
            fill_color=color,
            color=color,
            weight=1,
            tooltip=f"Hex: {hexagon}<br>{metric_col}: {metric}",
        ).add_to(map)

    map_bounds = _hex_bounds(df, "boundary")
    map.fit_bounds(map_bounds)

    return map
