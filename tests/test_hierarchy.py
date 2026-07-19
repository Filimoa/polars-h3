"""
FIXME: uncompact stuff
"""

import polars as pl
import pytest

import polars_h3 as plh3


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": 586265647244115967,
                "output": 581764796395814911,
                "schema": {"input": pl.UInt64},
            },
            id="uint64_input",
        ),
        pytest.param(
            {
                "input": 586265647244115967,
                "output": 581764796395814911,
                "schema": {"input": pl.Int64},
            },
            id="int64_input",
        ),
        pytest.param(
            {
                "input": "822d57fffffffff",
                "output": "812d7ffffffffff",
                "schema": None,
            },
            id="string_input",
        ),
    ],
)
def test_cell_to_parent_valid(test_params):
    df = pl.DataFrame(
        {"input": [test_params["input"]]}, schema=test_params["schema"]
    ).with_columns(parent=plh3.cell_to_parent("input", 1))
    assert df["parent"].to_list()[0] == test_params["output"]


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": 586265647244115967,
                "output": 595272305332977663,
                "schema": {"input": pl.UInt64},
            },
            id="uint64_input",
        ),
        pytest.param(
            {
                "input": 586265647244115967,
                "output": 595272305332977663,
                "schema": {"input": pl.Int64},
            },
            id="int64_input",
        ),
        pytest.param(
            {
                "input": "822d57fffffffff",
                "output": "842d501ffffffff",
                "schema": None,
            },
            id="string_input",
        ),
    ],
)
def test_cell_to_center_child_valid(test_params):
    df = pl.DataFrame(
        {"input": [test_params["input"]]}, schema=test_params["schema"]
    ).with_columns(child=plh3.cell_to_center_child("input", 4))
    assert df["child"].to_list()[0] == test_params["output"]


@pytest.mark.parametrize(
    "test_params",
    [
        pytest.param(
            {
                "input": 586265647244115967,
                "output": [
                    590768765835149311,
                    590768834554626047,
                    590768903274102783,
                    590768971993579519,
                    590769040713056255,
                    590769109432532991,
                    590769178152009727,
                ],
                "schema": {"input": pl.UInt64},
            },
            id="uint64_input",
        ),
        pytest.param(
            {
                "input": 586265647244115967,
                "output": [
                    590768765835149311,
                    590768834554626047,
                    590768903274102783,
                    590768971993579519,
                    590769040713056255,
                    590769109432532991,
                    590769178152009727,
                ],
                "schema": {"input": pl.Int64},
            },
            id="int64_input",
        ),
        pytest.param(
            {
                "input": "822d57fffffffff",
                "output": [
                    "832d50fffffffff",
                    "832d51fffffffff",
                    "832d52fffffffff",
                    "832d53fffffffff",
                    "832d54fffffffff",
                    "832d55fffffffff",
                    "832d56fffffffff",
                ],
                "schema": None,
            },
            id="string_input",
        ),
    ],
)
def test_cell_to_children_valid(test_params):
    df = pl.DataFrame(
        {"input": [test_params["input"]]}, schema=test_params["schema"]
    ).with_columns(children=plh3.cell_to_children("input", 3))
    assert df["children"].to_list()[0] == test_params["output"]


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
        df.with_columns(parent=plh3.cell_to_parent("h3_cell", resolution))

    with pytest.raises(ValueError):
        df.with_columns(child=plh3.cell_to_center_child("h3_cell", resolution))

    with pytest.raises(ValueError):
        df.with_columns(children=plh3.cell_to_children("h3_cell", resolution))


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
    ).with_columns(plh3.compact_cells("h3_cells").list.sort().alias("compacted"))
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


def test_compact_full_child_set_to_parent_and_reject_duplicates():
    children = [
        "88283080d1fffff",
        "88283080d3fffff",
        "88283080d5fffff",
        "88283080d7fffff",
        "88283080d9fffff",
        "88283080dbfffff",
        "88283080ddfffff",
    ]
    compacted = pl.DataFrame({"cells": [children]}).select(
        plh3.compact_cells("cells").alias("cells")
    )
    assert compacted["cells"].to_list() == [["87283080dffffff"]]

    with pytest.raises(pl.exceptions.ComputeError, match="duplicate indices"):
        pl.DataFrame({"cells": [[children[0], children[0]]]}).select(
            plh3.compact_cells("cells")
        )


def test_uncompact_cells_valid():
    df = pl.DataFrame({"h3_cells": [[581764796395814911]]}).with_columns(
        uncompacted=plh3.uncompact_cells("h3_cells", 2)
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
    result = pl.DataFrame({"h3_cells": [[]]}).with_columns(
        compacted=plh3.compact_cells("h3_cells"),
        uncompacted=plh3.uncompact_cells("h3_cells", 2),
    )
    assert result["compacted"].to_list() == [[]]
    assert result["uncompacted"].to_list() == [[]]


@pytest.mark.parametrize(
    "cell,resolution,expected",
    [
        ("87283080dffffff", 7, 1),
        ("87283080dffffff", 8, 7),
        ("87283080dffffff", 9, 49),
        ("870800000ffffff", 7, 1),
        ("870800000ffffff", 8, 6),
        ("870800000ffffff", 9, 41),
        ("806dfffffffffff", 15, 4_747_561_509_943),
        ("8009fffffffffff", 15, 3_956_301_258_286),
    ],
)
def test_cell_to_children_size_upstream_vectors(cell, resolution, expected):
    result = pl.DataFrame({"cell": [cell]}).select(
        plh3.cell_to_children_size("cell", resolution).alias("size")
    )
    assert result["size"].to_list() == [expected]


@pytest.mark.parametrize(
    "parent_resolution,expected_position", [(8, 0), (7, 6), (6, 41)]
)
def test_child_position_known_values_and_roundtrip(
    parent_resolution, expected_position
):
    child = "88283080ddfffff"
    frame = pl.DataFrame({"child": [child]}).with_columns(
        parent=plh3.cell_to_parent("child", parent_resolution),
        position=plh3.cell_to_child_pos("child", parent_resolution),
    )
    assert frame["position"].to_list() == [expected_position]

    roundtrip = frame.select(
        plh3.child_pos_to_cell("parent", "position", 8).alias("child")
    )
    assert roundtrip["child"].to_list() == [child]


def test_child_pos_to_cell_accepts_signed_positions_and_broadcasts():
    frame = pl.DataFrame(
        {
            "parent": ["87283080dffffff", "87283080dffffff"],
            "position": [6, 0],
        }
    ).select(plh3.child_pos_to_cell("parent", "position", 8).alias("child"))
    assert frame["child"].to_list() == ["88283080ddfffff", "88283080d1fffff"]
