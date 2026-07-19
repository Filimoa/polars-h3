import polars as pl
import pytest

from polars_h3 import graphing


@pytest.mark.parametrize(
    "plot,args",
    [
        (graphing.plot_hex_outlines, {"hex_id_col": "cell"}),
        (
            graphing.plot_hex_fills,
            {"hex_id_col": "cell", "metric_col": "metric"},
        ),
    ],
)
def test_plot_helpers_reject_empty_dataframes_before_loading_optional_deps(plot, args):
    with pytest.raises(ValueError, match="DataFrame is empty"):
        plot(pl.DataFrame(), **args)
