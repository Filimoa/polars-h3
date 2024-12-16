from typing import Any, Literal, Union

import polars as pl

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


def plot_hex_outlines(
    df: pl.DataFrame,
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
