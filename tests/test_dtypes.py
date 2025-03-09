import polars as pl
import pytest

import polars_h3 as plh3


def test_full_null_latlng():
    df = pl.DataFrame({"lat": [None] * 10000, "lng": [None] * 10000})
    with pytest.raises(pl.exceptions.ComputeError) as exc_info:
        df.with_columns(plh3.latlng_to_cell("lat", "lng", 9, return_dtype=pl.UInt64))
    # Check that the error message does not contain "panic"
    assert "panic" not in str(exc_info.value).lower()


def test_float32_latlng():
    df = pl.DataFrame(
        {
            "lat": [40.7128] * 10,
            "lng": [-74.006] * 10,
        },
        schema={"lat": pl.Float32, "lng": pl.Float32},
    )

    df.with_columns(plh3.latlng_to_cell("lat", "lng", 9, return_dtype=pl.UInt64))


@pytest.mark.parametrize(
    "test_params",
    [
        # --------------------------
        # Indexing Functions
        # --------------------------
        pytest.param(
            {
                "df": pl.DataFrame(
                    {
                        "lat": [40.7128] * 99 + [None],
                        "lng": [-74.006] * 99 + [None],
                    },
                ),
                "func": plh3.latlng_to_cell("lat", "lng", 9, return_dtype=pl.UInt64),
                "error": None,
            },
            id="latlng_to_cell",
        ),
        pytest.param(
            {
                "df": pl.DataFrame(
                    {
                        "h3_cell": [586265647244115967] * 99 + [None],
                    }
                ),
                "func": plh3.cell_to_boundary("h3_cell"),
                "error": None,
            },
            id="cell_to_boundary",
        ),
        pytest.param(
            {
                "df": pl.DataFrame(
                    {
                        "h3_cell": [586265647244115967] * 99 + [None],
                    }
                ),
                "func": plh3.cell_to_lat("h3_cell"),
                "error": None,
            },
            id="cell_to_lat",
        ),
        pytest.param(
            {
                "df": pl.DataFrame(
                    {
                        "h3_cell": [586265647244115967] * 99 + [None],
                    }
                ),
                "func": plh3.cell_to_lng("h3_cell"),
                "error": None,
            },
            id="cell_to_lng",
        ),
        pytest.param(
            {
                "df": pl.DataFrame(
                    {
                        "h3_cell": [586265647244115967] * 99 + [None],
                    }
                ),
                "func": plh3.cell_to_latlng("h3_cell"),
                "error": None,
            },
            id="cell_to_latlng",
        ),
        # --------------------------
        # Hierarchy Functions
        # --------------------------
        pytest.param(
            {
                "df": pl.DataFrame(
                    {
                        "h3_cell": [586265647244115967] * 99 + [None],
                    }
                ),
                "func": plh3.cell_to_parent("h3_cell", 1),
                "error": None,
            },
            id="cell_to_parent",
        ),
        pytest.param(
            {
                "df": pl.DataFrame(
                    {
                        "h3_cell": [586265647244115967] * 99 + [None],
                    }
                ),
                "func": plh3.cell_to_children("h3_cell", 3),
                "error": None,
            },
            id="cell_to_children",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"h3_cell": [586265647244115967] * 99 + [None]}),
                "func": plh3.cell_to_center_child("h3_cell", 4),
                "error": None,
            },
            id="cell_to_center_child_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"h3_cell": [586265647244115967] * 99 + [None]}),
                "func": plh3.cell_to_children("h3_cell", 3),
                "error": None,
            },
            id="cell_to_children_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"h3_cell": [586265647244115967] * 99 + [None]}),
                "func": plh3.cell_to_child_pos("h3_cell", 0),
                "error": None,
            },
            id="cell_to_child_pos_null",
        ),
        # not sure why this is not crashing?
        # pytest.param(
        #     {
        #         "df": pl.DataFrame(
        #             {
        #                 "h3_cell": [586265647244115967] * 99 + [None],
        #                 "pos": [0] * 100,
        #             },
        #             schema={"h3_cell": pl.UInt64, "pos": pl.Int8},
        #         ),
        #         "func": plh3.child_pos_to_cell("h3_cell", "pos", 1),
        #         "error": None,
        #     },
        #     id="child_pos_to_cell_null",
        # ),
        # not sure why this is not crashing?
        # pytest.param(
        #     {
        #         "df": pl.DataFrame(
        #             {
        #                 "h3_cells": [
        #                     [
        #                         586265647244115967,
        #                         586260699441790975,
        #                         586244756523188223,
        #                         586245306279002111,
        #                         586266196999929855,
        #                         586264547732488191,
        #                         586267846267371519,
        #                     ]
        #                 ]
        #                 * 99
        #                 + [[None]],
        #             }
        #         ),
        #         "func": plh3.compact_cells("h3_cells"),
        #         "error": None,
        #     },
        #     id="compact_cells_null",
        # ),
        # pytest.param(
        #     {
        #         "df": pl.DataFrame(
        #             {
        #                 "h3_cells": [[581764796395814911]] * 99 + [[None]],
        #             }
        #         ),
        #         "func": plh3.uncompact_cells("h3_cells", 2),
        #         "error": None,
        #     },
        #     id="uncompact_cells_null",
        # ),
        # --------------------------
        # Inspection Functions
        # --------------------------
        pytest.param(
            {
                "df": pl.DataFrame({"h3_cell": [586265647244115967] * 99 + [None]}),
                "func": plh3.get_resolution("h3_cell"),
                "error": None,
            },
            id="get_resolution_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"h3_str": ["822d57fffffffff"] * 99 + [None]}),
                "func": plh3.str_to_int("h3_str"),
                "error": None,
            },
            id="str_to_int_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"h3_cell": [586265647244115967] * 99 + [None]}),
                "func": plh3.int_to_str("h3_cell"),
                "error": None,
            },
            id="int_to_str_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"h3_cell": [586265647244115967] * 99 + [None]}),
                "func": plh3.is_valid_cell("h3_cell"),
                "error": None,
                "num_nulls_expected": 0,
            },
            id="is_valid_cell_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"h3_cell": [586265647244115967] * 99 + [None]}),
                "func": plh3.is_pentagon("h3_cell"),
                "error": None,
                "num_nulls_expected": 0,
            },
            id="is_pentagon_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"h3_cell": [586265647244115967] * 99 + [None]}),
                "func": plh3.is_res_class_III("h3_cell"),
                "error": None,
                "num_nulls_expected": 0,
            },
            id="is_res_class_III_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"h3_cell": [586265647244115967] * 99 + [None]}),
                "func": plh3.get_icosahedron_faces("h3_cell"),
                "error": None,
            },
            id="get_icosahedron_faces_null",
        ),
        # --------------------------
        # Traversal Functions
        # --------------------------
        pytest.param(
            {
                "df": pl.DataFrame(
                    {
                        "origin": [586265647244115967] * 99 + [None],
                        "dest": [586265647244115967] * 100,
                    }
                ),
                "func": plh3.grid_distance("origin", "dest"),
                "error": None,
            },
            id="grid_distance_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame(
                    {
                        "cell": [586265647244115967] * 99 + [None],
                        "k": [1] * 100,
                    }
                ),
                "func": plh3.grid_ring("cell", "k"),
                "error": None,
            },
            id="grid_ring_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame(
                    {
                        "cell": [586265647244115967] * 99 + [None],
                        "k": [1] * 100,
                    }
                ),
                "func": plh3.grid_disk("cell", "k"),
                "error": None,
            },
            id="grid_disk_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame(
                    {
                        "origin": [586265647244115967] * 99 + [None],
                        "destination": [586265647244115967] * 100,
                    }
                ),
                "func": plh3.grid_path_cells("origin", "destination"),
                "error": None,
            },
            id="grid_path_cells_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame(
                    {
                        "origin": [586265647244115967] * 99 + [None],
                        "dest": [586265647244115967] * 100,
                    }
                ),
                "func": plh3.cell_to_local_ij("origin", "dest"),
                "error": None,
            },
            id="cell_to_local_ij_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame(
                    {
                        "origin": [605034941285138431] * 99 + [None],
                        "i": [-123] * 100,
                        "j": [-177] * 100,
                    }
                ),
                "func": plh3.local_ij_to_cell("origin", "i", "j"),
                "error": None,
            },
            id="local_ij_to_cell_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"h3_cell": [586265647244115967] * 99 + [None]}),
                "func": plh3.cell_to_vertex("h3_cell", 0),
                "error": None,
            },
            id="cell_to_vertex_null",
        ),
        # --------------------------
        # Vertex Functions
        # --------------------------
        pytest.param(
            {
                "df": pl.DataFrame({"h3_cell": [586265647244115967] * 99 + [None]}),
                "func": plh3.cell_to_vertexes("h3_cell"),
                "error": None,
            },
            id="cell_to_vertexes_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"vertex": [2459626752788398079] * 99 + [None]}),
                "func": plh3.vertex_to_latlng("vertex"),
                "error": None,
            },
            id="vertex_to_latlng_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"vertex": [2459626752788398079] * 99 + [None]}),
                "func": plh3.is_valid_vertex("vertex"),
                "error": None,
                "num_nulls_expected": 0,
            },
            id="is_valid_vertex_null",
        ),
        # --------------------------
        # Edge Functions
        # --------------------------
        pytest.param(
            {
                "df": pl.DataFrame(
                    {
                        "origin": [599686042433355775] * 99 + [None],
                        "dest": [599686029548453887] * 100,
                    },
                    schema={"origin": pl.UInt64, "dest": pl.UInt64},
                ),
                "func": plh3.are_neighbor_cells("origin", "dest"),
                "error": None,
                "num_nulls_expected": 0,
            },
            id="are_neighbor_cells_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame(
                    {
                        "origin": [599686042433355775] * 99 + [None],
                        "destination": [599686030622195711] * 100,
                    }
                ),
                "func": plh3.cells_to_directed_edge("origin", "destination"),
                "error": None,
            },
            id="cells_to_directed_edge_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"edge": [1608492358964346879] * 99 + [None]}),
                "func": plh3.is_valid_directed_edge("edge"),
                "error": None,
                "num_nulls_expected": 0,
            },
            id="is_valid_directed_edge_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"edge": [1608492358964346879] * 99 + [None]}),
                "func": plh3.get_directed_edge_origin("edge"),
                "error": None,
            },
            id="get_directed_edge_origin_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"edge": [1608492358964346879] * 99 + [None]}),
                "func": plh3.get_directed_edge_destination("edge"),
                "error": None,
            },
            id="get_directed_edge_destination_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"edge": [1608492358964346879] * 99 + [None]}),
                "func": plh3.directed_edge_to_cells("edge"),
                "error": None,
            },
            id="directed_edge_to_cells_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"h3_cell": [586265647244115967] * 99 + [None]}),
                "func": plh3.origin_to_directed_edges("h3_cell"),
                "error": None,
            },
            id="origin_to_directed_edges_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"edge": [1608492358964346879] * 99 + [None]}),
                "func": plh3.directed_edge_to_boundary("edge"),
                "error": None,
            },
            id="directed_edge_to_boundary_null",
        ),
        # --------------------------
        # Metrics Functions
        # --------------------------
        pytest.param(
            {
                "df": pl.DataFrame({"h3_cell": [586265647244115967] * 99 + [None]}),
                "func": plh3.cell_area("h3_cell", unit="km^2"),
                "error": None,
            },
            id="cell_area_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"h3_cell": [1608492358964346879] * 99 + [None]}),
                "func": plh3.edge_length("h3_cell", unit="km"),
                "error": None,
            },
            id="edge_length_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame(
                    {
                        "lat1": [40.7128] * 99 + [None],
                        "lng1": [-74.0060] * 99 + [None],
                        "lat2": [42.3601] * 100,
                        "lng2": [-71.0589] * 100,
                    }
                ),
                "func": plh3.great_circle_distance(
                    "lat1", "lng1", "lat2", "lng2", "km"
                ),
                "error": None,
            },
            id="great_circle_distance_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"resolution": [5] * 99 + [None]}),
                "func": plh3.average_hexagon_area(pl.col("resolution"), "km^2"),
                "error": None,
            },
            id="average_hexagon_area_null",
        ),
        pytest.param(
            {
                "df": pl.DataFrame({"resolution": [1] * 99 + [None]}),
                "func": plh3.average_hexagon_edge_length(pl.col("resolution"), "km"),
                "error": None,
            },
            id="average_hexagon_edge_length_null",
        ),
        # pytest.param(
        #     {
        #         "df": pl.DataFrame(
        #             {"resolution": [0] * 99 + [None]},
        #             # schema={"resolution": pl.UInt8},
        #         ),
        #         "func": plh3.get_num_cells("resolution"),
        #         "error": None,
        #     },
        #     id="get_num_cells_null",
        # ),
        pytest.param(
            {
                "df": pl.DataFrame({"resolution": [5] * 99 + [None]}),
                "func": plh3.get_pentagons("resolution"),
                "error": None,
            },
            id="get_pentagons_null",
        ),
    ],
)
def test_single_null_in_data_does_not_throw_panic(test_params):
    """
    Some funcs will error out if a single null is supplied. We want to make sure we're wrapping the error so the user does not see an unhelpful panic. If error is None, we expect function to just return None for null values.
    """
    if test_params["error"]:
        with pytest.raises(pl.exceptions.ComputeError) as exc_info:
            test_params["df"].with_columns(test_params["func"])

        exception_msg = str(exc_info.value).lower()
        assert test_params["error"]["error_msg"] in exception_msg
        assert "panic" not in exception_msg
    else:
        df = test_params["df"].with_columns(res=test_params["func"])

        num_nulls_expected = test_params.get("num_nulls_expected", 1)
        assert df["res"].null_count() == num_nulls_expected
        assert df["res"].count() == 100 - num_nulls_expected
