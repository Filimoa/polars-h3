from typing import Union

import polars as pl
import pytest

import polars_h3


@pytest.mark.parametrize(
    "vertex, schema, expected_valid",
    [
        pytest.param(["2222597fffffffff"], None, True, id="valid_str_vertex"),
        pytest.param(["823d6ffffffffff"], None, False, id="invalid_str_vertex"),
        pytest.param([0], {"vertex": pl.UInt64}, False, id="invalid_int_vertex"),
        pytest.param(
            [2459626752788398079], {"vertex": pl.UInt64}, True, id="valid_int_vertex"
        ),
    ],
)
def test_is_valid_vertex(
    vertex: list[Union[int, str]],
    schema: Union[dict[str, pl.DataType], None],
    expected_valid: bool,
):
    df = pl.DataFrame({"vertex": vertex}, schema=schema).with_columns(
        valid=polars_h3.is_valid_vertex("vertex")
    )
    assert df["valid"][0] == expected_valid


@pytest.mark.parametrize(
    "h3_cell, schema, expected_vertexes",
    [
        # Example from provided queries:
        # '823d6ffffffffff' returns a kjnown set of vertex indexes
        pytest.param(
            ["823d6ffffffffff"],
            None,
            [
                2459626752788398079,
                2676216249809108991,
                2604158655771181055,
                2387553765587681279,
                2315496171549753343,
                2531684346826326015,
            ],
            id="valid_cell_vertexes_str",
        ),
        # Invalid cell returns None
        pytest.param(["fffffffffffffff"], None, None, id="invalid_cell_vertexes_str"),
        # UInt64 type input
        pytest.param(
            [599686042433355775],
            {"h3_cell": pl.UInt64},
            [
                2473183459502194687,
                2545241069646249983,
                2329068295048658943,
                2689356265238298623,
                2473183460575936511,
                2545241053540122623,
            ],
            id="uint64_cell_vertexes",
        ),
    ],
)
def test_cell_to_vertexes(
    h3_cell: list[Union[int, str]],
    schema: Union[dict[str, pl.DataType], None],
    expected_vertexes: Union[list[int], None],
):
    df = pl.DataFrame({"h3_cell": h3_cell}, schema=schema).with_columns(
        vertexes=polars_h3.cell_to_vertexes("h3_cell")
    )

    if expected_vertexes is None:
        # Expecting None means we should have a null return
        assert df["vertexes"].to_list()[0] is None
    else:
        # Compare lists
        assert df["vertexes"].to_list()[0] == expected_vertexes


@pytest.mark.parametrize(
    "h3_cell, vertex_num, expected_vertex",
    [
        (["823d6ffffffffff"], 0, 2459626752788398079),
        ([586265647244115967], 0, 2675930926541701119),
    ],
)
def test_cell_to_vertex_valid(h3_cell, vertex_num, expected_vertex):
    df = pl.DataFrame({"h3_cell": h3_cell}).with_columns(
        vertex=polars_h3.cell_to_vertex("h3_cell", vertex_num)
    )
    assert df["vertex"][0] == expected_vertex


def test_cell_to_vertex_invalid_vertex_num():
    df = pl.DataFrame({"h3_cell": "823d6ffffffffff"})
    with pytest.raises(pl.exceptions.ComputeError):
        df.with_columns(vertex=polars_h3.cell_to_vertex("h3_cell", -1))


@pytest.mark.parametrize(
    "vertex, schema, expected_coords",
    [
        (["2222597fffffffff"], None, [39.38084284181813, 88.57496213785487]),
        # If this vertex also returns coords similar to above:
        (
            [2459626752788398079],
            {"vertex": pl.UInt64},
            [39.38084284181812, 88.57496213785487],
        ),
        (["823d6ffffffffff"], None, None),  # Invalid vertex, expect None
    ],
)
def test_vertex_to_latlng(vertex, schema, expected_coords):
    df = pl.DataFrame({"vertex": vertex}, schema=schema).with_columns(
        coords=polars_h3.vertex_to_latlng("vertex")
    )

    result = df["coords"].to_list()[0]
    if expected_coords is None:
        assert result is None
    else:
        lat, lng = result
        assert pytest.approx(lat, 0.000001) == expected_coords[0]
        assert pytest.approx(lng, 0.000001) == expected_coords[1]
