"""
FIXME: uncompact stuff
"""

from typing import Dict, Union, List
import pytest
import polars as pl
import polars_h3


@pytest.mark.parametrize(
    "h3_cell, schema",
    [
        pytest.param(
            [586265647244115967],
            {"h3_cell": pl.UInt64},
            id="uint64_input",
        ),
        pytest.param(
            [586265647244115967],
            {"h3_cell": pl.Int64},
            id="int64_input",
        ),
        pytest.param(
            ["822d57fffffffff"],
            None,
            id="string_input",
        ),
    ],
)
def test_cell_to_parent_valid(
    h3_cell: List[Union[int, str]], schema: Union[Dict[str, pl.DataType], None]
):
    df = pl.DataFrame({"h3_cell": h3_cell}, schema=schema).with_columns(
        parent=polars_h3.cell_to_parent("h3_cell", 1)
    )
    assert df["parent"].to_list()[0] == 581764796395814911


@pytest.mark.parametrize(
    "h3_cell, schema",
    [
        pytest.param(
            [586265647244115967],
            {"h3_cell": pl.UInt64},
            id="uint64_input",
        ),
        pytest.param(
            [586265647244115967],
            {"h3_cell": pl.Int64},
            id="int64_input",
        ),
        pytest.param(
            ["822d57fffffffff"],
            None,
            id="string_input",
        ),
    ],
)
def test_cell_to_center_child_valid(
    h3_cell: List[Union[int, str]], schema: Union[Dict[str, pl.DataType], None]
):
    df = pl.DataFrame({"h3_cell": h3_cell}, schema=schema).with_columns(
        child=polars_h3.cell_to_center_child("h3_cell", 4)
    )
    assert df["child"].to_list()[0] == 595272305332977663


@pytest.mark.parametrize(
    "h3_cell, schema",
    [
        pytest.param(
            [586265647244115967],
            {"h3_cell": pl.UInt64},
            id="uint64_input",
        ),
        pytest.param(
            [586265647244115967],
            {"h3_cell": pl.Int64},
            id="int64_input",
        ),
        pytest.param(
            ["822d57fffffffff"],
            None,
            id="string_input",
        ),
    ],
)
def test_cell_to_children_valid(
    h3_cell: List[Union[int, str]], schema: Union[Dict[str, pl.DataType], None]
):
    df = pl.DataFrame({"h3_cell": h3_cell}, schema=schema).with_columns(
        children=polars_h3.cell_to_children("h3_cell", 3)
    )
    assert df["children"].to_list()[0] == [
        590768765835149311,
        590768834554626047,
        590768903274102783,
        590768971993579519,
        590769040713056255,
        590769109432532991,
        590769178152009727,
    ]


@pytest.mark.parametrize(
    "resolution",
    [
        pytest.param(-1, id="negative_resolution"),
        pytest.param(30, id="too_high_resolution"),
    ],
)
def test_invalid_resolutions(resolution: int):
    df = pl.DataFrame({"h3_cell": [586265647244115967]})

    with pytest.raises(ValueError):
        df.with_columns(parent=polars_h3.cell_to_parent("h3_cell", resolution))

    with pytest.raises(ValueError):
        df.with_columns(child=polars_h3.cell_to_center_child("h3_cell", resolution))

    with pytest.raises(ValueError):
        df.with_columns(children=polars_h3.cell_to_children("h3_cell", resolution))


def test_compact_cells_valid():
    df = pl.DataFrame(
        {
            "h3_cells": [
                [
                    586265647244115967,
                    586260699441790975,
                    586244756523188223,
                    586245306279002111,
                    586266196999929855,
                    586264547732488191,
                    586267846267371519,
                ]
            ]
        }
    ).with_columns(polars_h3.compact_cells("h3_cells").list.sort().alias("compacted"))
    assert df["compacted"].to_list()[0] == sorted(
        [
            586265647244115967,
            586260699441790975,
            586244756523188223,
            586245306279002111,
            586266196999929855,
            586264547732488191,
            586267846267371519,
        ]
    )


def test_uncompact_cells_valid():
    df = pl.DataFrame({"h3_cells": [[581764796395814911]]}).with_columns(
        uncompacted=polars_h3.uncompact_cells("h3_cells", 2)
    )
    assert df["uncompacted"].to_list()[0] == [
        586264547732488191,
        586265097488302079,
        586265647244115967,
        586266196999929855,
        586266746755743743,
        586267296511557631,
        586267846267371519,
    ]


def test_uncompact_cells_empty():
    with pytest.raises(pl.exceptions.ComputeError):
        pl.DataFrame({"h3_cells": [[]]}).with_columns(
            uncompacted=polars_h3.uncompact_cells("h3_cells", 2)
        )
