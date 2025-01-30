# Folium Integration

Functions that use Folium to visualize H3 cells on a map.

---

## `plot_hex_outlines`

Plot hexagon outlines on a Folium map.

```python
plot_hex_outlines(
    df: pl.DataFrame,
    hex_id_col: str,
    map: Any | None = None,
    outline_color: str = "red",
    map_size: Literal["medium", "large"] = "medium",
) -> Any
```

**Parameters**

- **df** : pl.DataFrame  
  A DataFrame that must contain a column of H3 cell IDs.
- **hex_id_col** : str  
  Column name in `df` containing H3 cell IDs (hexagon identifiers).
- **map** : folium.Map or None  
  An existing Folium map object on which to plot. If `None`, a new map is created.
- **outline_color** : str  
  Color used to outline the hexagons. Defaults to `"red"`.
- **map_size** : `{"medium", "large"}`  
  The size of the displayed map. `"medium"` sets width and height to 50%; `"large"` sets them to 100%.

**Returns**

- **Any**  
  A Folium map object with hexagon outlines added.

**Examples**

```python
>>> df = pl.DataFrame({
...     "hex_id": [599686042433355775, 599686042433355776]
... })
>>> # Suppose 'hex_id' contains valid H3 cell indices
>>> my_map = polars_h3_folium.plot_hex_outlines(df, "hex_id", outline_color="blue")
>>> my_map
```

**Errors**

- `ValueError` : If the input DataFrame is empty.
- `ImportError` : If `folium` is not installed.

---

## `plot_hex_fills`

Render filled hexagonal cells on a Folium map, colorized by a specified metric.

```python
plot_hex_fills(
    df: pl.DataFrame,
    hex_id_col: str,
    metric_col: str,
    map: Any | None = None,
    map_size: Literal["medium", "large"] = "medium",
) -> Any
```

**Parameters**

- **df** : pl.DataFrame  
  A DataFrame that must contain columns for H3 cell IDs and a metric to color by.
- **hex_id_col** : str  
  Column name containing H3 cell IDs.
- **metric_col** : str  
  Column name containing metric values for colorization.
- **map** : folium.Map or None  
  An existing Folium map object. If `None`, a new map is created.
- **map_size** : `{"medium", "large"}`  
  The size of the displayed map. `"medium"` sets 50% width/height, `"large"` sets 100%.

**Returns**

- **Any**  
  A Folium map object with filled hexagons colorized by the specified metric.

**Examples**

```python
>>> df = pl.DataFrame({
...     "hex_id": [599686042433355775, 599686042433355776],
...     "some_metric": [10.0, 42.0],
... })
>>> # 'hex_id' and 'some_metric' must be valid
>>> my_map = polars_h3_folium.plot_hex_fills(df, "hex_id", "some_metric")
>>> my_map
```

![CleanShot 2024-12-08 at 00 26 22](https://github.com/user-attachments/assets/2e707bfc-1a29-43b5-9260-723d776e5dad)

**Errors**

- `ValueError` : If the input DataFrame is empty.
- `ImportError` : If `folium` or `matplotlib` is not installed.

---

**Note**  
These functions leverage [Folium](https://python-visualization.github.io/folium/) for mapping and [Matplotlib](https://matplotlib.org) for color scaling in `plot_hex_fills`. Ensure both are installed to visualize your hexes properly.
