import struct

import h3
import polars as pl
import pytest

import polars_h3 as plh3

POLYGON_WKT = (
    "POLYGON((-122.42 37.77,-122.40 37.77,-122.40 37.79,"
    "-122.42 37.79,-122.42 37.77))"
)
POLYGON_GEO = {
    "type": "Polygon",
    "coordinates": [
        [
            [-122.42, 37.77],
            [-122.40, 37.77],
            [-122.40, 37.79],
            [-122.42, 37.79],
            [-122.42, 37.77],
        ]
    ],
}


def _cells_for_wkt(wkt: str, resolution: int = 9) -> list[int]:
    return (
        pl.DataFrame({"wkt": [wkt]})
        .select(plh3.polygon_to_cells("wkt", resolution))
        .item()
        .to_list()
    )


def _polygon_wkb(rings: list[list[list[float]]]) -> bytes:
    value = bytearray(struct.pack("<BI", 1, 3))
    value.extend(struct.pack("<I", len(rings)))
    for ring in rings:
        value.extend(struct.pack("<I", len(ring)))
        for lng, lat in ring:
            value.extend(struct.pack("<dd", lng, lat))
    return bytes(value)


def _multipolygon_wkb(polygons: list[bytes]) -> bytes:
    return struct.pack("<BII", 1, 6, len(polygons)) + b"".join(polygons)


def _dimensional_polygon_wkb(type_id: int, dimensions: int, byte_order: str) -> bytes:
    marker = 1 if byte_order == "<" else 0
    ring = [
        (-122.42, 37.77),
        (-122.40, 37.77),
        (-122.40, 37.79),
        (-122.42, 37.79),
        (-122.42, 37.77),
    ]
    value = bytearray(bytes([marker]))
    value.extend(struct.pack(f"{byte_order}III", type_id, 1, len(ring)))
    for longitude, latitude in ring:
        coordinates = [longitude, latitude, *([1.0] * (dimensions - 2))]
        value.extend(struct.pack(f"{byte_order}{dimensions}d", *coordinates))
    return bytes(value)


def _ewkb_polygon(
    *,
    byte_order: str = "<",
    has_z: bool = False,
    has_m: bool = False,
    srid: int | None = 4326,
) -> bytes:
    marker = 1 if byte_order == "<" else 0
    type_id = 3
    type_id |= 0x8000_0000 if has_z else 0
    type_id |= 0x4000_0000 if has_m else 0
    type_id |= 0x2000_0000 if srid is not None else 0
    dimensions = 2 + has_z + has_m
    ring = POLYGON_GEO["coordinates"][0]

    value = bytearray(bytes([marker]))
    value.extend(struct.pack(f"{byte_order}I", type_id))
    if srid is not None:
        value.extend(struct.pack(f"{byte_order}I", srid))
    value.extend(struct.pack(f"{byte_order}II", 1, len(ring)))
    for longitude, latitude in ring:
        coordinates = [longitude, latitude, *([1.0] * (dimensions - 2))]
        value.extend(struct.pack(f"{byte_order}{dimensions}d", *coordinates))
    return bytes(value)


def _ewkb_multipolygon(*, byte_order: str = "<", srid: int = 4326) -> bytes:
    marker = 1 if byte_order == "<" else 0
    value = bytearray(bytes([marker]))
    value.extend(struct.pack(f"{byte_order}II", 0x2000_0006, srid))
    value.extend(struct.pack(f"{byte_order}I", 1))
    value.extend(_ewkb_polygon(byte_order=byte_order, srid=None))
    return bytes(value)


def test_polygon_wkt_to_cells_matches_h3_reference():
    actual = set(_cells_for_wkt(POLYGON_WKT))
    expected = {h3.str_to_int(cell) for cell in h3.geo_to_cells(POLYGON_GEO, 9)}

    assert actual == expected


def test_polygon_to_cells_accepts_wkb_binary():
    wkb = _polygon_wkb(POLYGON_GEO["coordinates"])
    actual = (
        pl.DataFrame({"geometry": [wkb]}, schema={"geometry": pl.Binary})
        .select(plh3.polygon_to_cells("geometry", 9))
        .item()
        .to_list()
    )
    expected = {h3.str_to_int(cell) for cell in h3.geo_to_cells(POLYGON_GEO, 9)}

    assert set(actual) == expected
    assert len(actual) == len(set(actual))


def test_polygon_to_cells_deduplicates_overlapping_wkb_multipolygon_members():
    polygon = _polygon_wkb(POLYGON_GEO["coordinates"])
    multipolygon = _multipolygon_wkb([polygon, polygon])
    frame = pl.DataFrame(
        {"geometry": [polygon, multipolygon]},
        schema={"geometry": pl.Binary},
    )

    polygon_cells, multipolygon_cells = (
        frame.select(plh3.polygon_to_cells("geometry", 9))
        .get_column("geometry")
        .to_list()
    )

    assert set(multipolygon_cells) == set(polygon_cells)
    assert len(multipolygon_cells) == len(set(multipolygon_cells))


def test_polygon_wkt_to_cells_compatibility_wrapper():
    frame = pl.DataFrame({"wkt": [POLYGON_WKT]})

    assert frame.select(plh3.polygon_wkt_to_cells("wkt", 9)).item().to_list() == (
        frame.select(plh3.polygon_to_cells("wkt", 9)).item().to_list()
    )


def test_polygon_wkt_to_cells_supports_multipolygons_and_deduplicates():
    multipolygon = (
        "MULTIPOLYGON("
        "((-122.42 37.77,-122.40 37.77,-122.40 37.79,"
        "-122.42 37.79,-122.42 37.77)),"
        "((-122.42 37.77,-122.40 37.77,-122.40 37.79,"
        "-122.42 37.79,-122.42 37.77)))"
    )

    assert _cells_for_wkt(multipolygon) == _cells_for_wkt(POLYGON_WKT)


def test_polygon_wkt_to_cells_supports_holes():
    polygon_with_hole = (
        "POLYGON("
        "(-122.43 37.76,-122.39 37.76,-122.39 37.80,"
        "-122.43 37.80,-122.43 37.76),"
        "(-122.415 37.775,-122.405 37.775,-122.405 37.785,"
        "-122.415 37.785,-122.415 37.775))"
    )
    geo = {
        "type": "Polygon",
        "coordinates": [
            [
                [-122.43, 37.76],
                [-122.39, 37.76],
                [-122.39, 37.80],
                [-122.43, 37.80],
                [-122.43, 37.76],
            ],
            [
                [-122.415, 37.775],
                [-122.405, 37.775],
                [-122.405, 37.785],
                [-122.415, 37.785],
                [-122.415, 37.775],
            ],
        ],
    }
    expected = {h3.str_to_int(cell) for cell in h3.geo_to_cells(geo, 9)}

    assert set(_cells_for_wkt(polygon_with_hole)) == expected


def test_polygon_to_cells_supports_antimeridian_crossings():
    polygon = "POLYGON((179.5 0.0,-179.5 0.0,-179.5 1.0," "179.5 1.0,179.5 0.0))"
    geo = {
        "type": "Polygon",
        "coordinates": [
            [
                [179.5, 0.0],
                [-179.5, 0.0],
                [-179.5, 1.0],
                [179.5, 1.0],
                [179.5, 0.0],
            ]
        ],
    }
    expected = {h3.str_to_int(cell) for cell in h3.geo_to_cells(geo, 5)}

    assert set(_cells_for_wkt(polygon, resolution=5)) == expected


@pytest.mark.parametrize("wkt", ["POLYGON EMPTY", "MULTIPOLYGON EMPTY"])
def test_polygon_to_cells_supports_empty_wkt_geometry_eager_and_lazy(wkt: str):
    frame = pl.DataFrame({"geometry": [wkt]})

    eager = frame.select(cells=plh3.polygon_to_cells("geometry", 5))
    lazy = frame.lazy().select(cells=plh3.polygon_to_cells("geometry", 5)).collect()

    assert eager.schema["cells"] == pl.List(pl.UInt64)
    assert eager.item().to_list() == []
    assert lazy.equals(eager)


def test_polygon_to_cells_skips_empty_multipolygon_members():
    polygon = "POLYGON((0 0,1 0,1 1,0 1,0 0))"
    multipolygon = "MULTIPOLYGON(EMPTY,((0 0,1 0,1 1,0 1,0 0)))"

    assert _cells_for_wkt(multipolygon, resolution=5) == _cells_for_wkt(
        polygon, resolution=5
    )


def test_polygon_to_cells_supports_zero_ring_wkb_polygon_eager_and_lazy():
    empty_polygon_wkb = struct.pack("<BII", 1, 3, 0)
    frame = pl.DataFrame(
        {"geometry": [empty_polygon_wkb]}, schema={"geometry": pl.Binary}
    )

    eager = frame.select(cells=plh3.polygon_to_cells("geometry", 5))
    lazy = frame.lazy().select(cells=plh3.polygon_to_cells("geometry", 5)).collect()

    assert eager.item().to_list() == []
    assert lazy.equals(eager)


@pytest.mark.parametrize(
    ("type_id", "dimensions", "byte_order"),
    [(3, 2, ">"), (1003, 3, "<"), (2003, 3, ">"), (3003, 4, "<")],
)
def test_polygon_to_cells_accepts_valid_wkb_endianness_and_dimensions(
    type_id: int, dimensions: int, byte_order: str
):
    wkb = _dimensional_polygon_wkb(type_id, dimensions, byte_order)
    frame = pl.DataFrame({"geometry": [wkb]}, schema={"geometry": pl.Binary})

    actual = frame.select(plh3.polygon_to_cells("geometry", 9)).item().to_list()

    assert actual == _cells_for_wkt(POLYGON_WKT)


@pytest.mark.parametrize(
    ("byte_order", "has_z", "has_m"),
    [("<", False, False), (">", True, False), ("<", False, True), (">", True, True)],
)
def test_polygon_to_cells_accepts_ewkb_srid_and_dimensions(
    byte_order: str, has_z: bool, has_m: bool
):
    ewkb = _ewkb_polygon(byte_order=byte_order, has_z=has_z, has_m=has_m)
    frame = pl.DataFrame({"geometry": [ewkb]}, schema={"geometry": pl.Binary})

    actual = frame.select(plh3.polygon_to_cells("geometry", 9)).item().to_list()

    assert actual == _cells_for_wkt(POLYGON_WKT)


@pytest.mark.parametrize("byte_order", ["<", ">"])
def test_polygon_to_cells_accepts_ewkb_multipolygon(byte_order: str):
    ewkb = _ewkb_multipolygon(byte_order=byte_order)
    frame = pl.DataFrame({"geometry": [ewkb]}, schema={"geometry": pl.Binary})

    actual = frame.select(plh3.polygon_to_cells("geometry", 9)).item().to_list()

    assert actual == _cells_for_wkt(POLYGON_WKT)


def test_polygon_to_cells_rejects_non_wgs84_ewkb_srid():
    ewkb = _ewkb_polygon(srid=3857)
    frame = pl.DataFrame({"geometry": [ewkb]}, schema={"geometry": pl.Binary})

    with pytest.raises(
        pl.exceptions.ComputeError, match="expected SRID 4326, got 3857"
    ):
        frame.select(plh3.polygon_to_cells("geometry", 9))


@pytest.mark.parametrize("ring_count", [1, 2])
def test_polygon_to_cells_rejects_declared_zero_point_wkb_rings(ring_count: int):
    malformed_wkb = (
        struct.pack("<BII", 1, 3, ring_count) + b"\x00\x00\x00\x00" * ring_count
    )
    frame = pl.DataFrame({"geometry": [malformed_wkb]}, schema={"geometry": pl.Binary})

    with pytest.raises(pl.exceptions.ComputeError, match="expected at least 4"):
        frame.select(plh3.polygon_to_cells("geometry", 5))


def test_polygon_to_cells_rejects_unclosed_wkb_ring():
    wkb = _polygon_wkb([[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]])
    frame = pl.DataFrame({"geometry": [wkb]}, schema={"geometry": pl.Binary})

    with pytest.raises(pl.exceptions.ComputeError, match="ring 0 is not closed"):
        frame.select(plh3.polygon_to_cells("geometry", 5))


@pytest.mark.parametrize(
    "wkt",
    [
        "POLYGON((0 0,1 0,1 1,0 1))",
        "POLYGON((0 0,2 0,2 2,0 2,0 0),(0.5 0.5,1 0.5,1 1,0.5 1))",
        "MULTIPOLYGON(((0 0,1 0,1 1,0 1)))",
    ],
)
def test_polygon_to_cells_rejects_unclosed_wkt_rings(wkt: str):
    with pytest.raises(pl.exceptions.ComputeError, match="ring .* is not closed"):
        _cells_for_wkt(wkt, resolution=5)


def test_polygon_to_cells_rejects_short_wkt_ring():
    with pytest.raises(pl.exceptions.ComputeError, match="expected at least 4"):
        _cells_for_wkt("POLYGON((0 0,1 0,0 0))", resolution=5)


@pytest.mark.parametrize("marker", [2, 255])
def test_polygon_to_cells_rejects_invalid_wkb_byte_order(marker: int):
    wkb = bytes([marker]) + struct.pack("<II", 3, 0)
    frame = pl.DataFrame({"geometry": [wkb]}, schema={"geometry": pl.Binary})

    with pytest.raises(pl.exceptions.ComputeError, match="byte-order marker"):
        frame.select(plh3.polygon_to_cells("geometry", 5))


def test_polygon_to_cells_rejects_wrong_multipolygon_child_type():
    wkb = (
        struct.pack("<BII", 1, 6, 1)
        + struct.pack("<BI", 1, 1)
        + struct.pack("<dd", 0.0, 0.0)
    )
    frame = pl.DataFrame({"geometry": [wkb]}, schema={"geometry": pl.Binary})

    with pytest.raises(pl.exceptions.ComputeError, match="nested Polygon"):
        frame.select(plh3.polygon_to_cells("geometry", 5))


def test_polygon_to_cells_rejects_trailing_wkb_bytes():
    wkb = struct.pack("<BII", 1, 3, 0) + b"junk"
    frame = pl.DataFrame({"geometry": [wkb]}, schema={"geometry": pl.Binary})

    with pytest.raises(pl.exceptions.ComputeError, match="trailing bytes"):
        frame.select(plh3.polygon_to_cells("geometry", 5))


def test_polygon_to_cells_still_rejects_malformed_non_empty_ring():
    with pytest.raises(pl.exceptions.ComputeError, match="expected at least 4"):
        _cells_for_wkt("POLYGON((0 0,1 1))", resolution=5)


def test_polygon_wkt_to_cells_preserves_null_rows():
    result = pl.DataFrame({"wkt": [POLYGON_WKT, None]}).select(
        cells=plh3.polygon_wkt_to_cells("wkt", 9)
    )

    assert result.schema["cells"] == pl.List(pl.UInt64)
    assert result["cells"][0] is not None
    assert result["cells"][1] is None


def test_polygon_to_cells_preserves_null_binary_rows():
    result = pl.DataFrame(
        {"geometry": [None]},
        schema={"geometry": pl.Binary},
    ).select(cells=plh3.polygon_to_cells("geometry", 9))

    assert result.schema["cells"] == pl.List(pl.UInt64)
    assert result.item() is None


def test_polygon_to_cells_preserves_chunked_binary_row_semantics():
    polygon = _polygon_wkb(POLYGON_GEO["coordinates"])
    multipolygon = _multipolygon_wkb([polygon, polygon])
    empty_polygon = struct.pack("<BII", 1, 3, 0)
    frame = pl.concat(
        [
            pl.DataFrame(
                {"row": [0, 1], "geometry": [polygon, None]},
                schema={"row": pl.Int64, "geometry": pl.Binary},
            ),
            pl.DataFrame(
                {"row": [2], "geometry": [empty_polygon]},
                schema={"row": pl.Int64, "geometry": pl.Binary},
            ),
            pl.DataFrame(
                {"row": [3], "geometry": [multipolygon]},
                schema={"row": pl.Int64, "geometry": pl.Binary},
            ),
        ],
        rechunk=False,
    )
    assert frame["geometry"].n_chunks() == 3

    eager = frame.select("row", cells=plh3.polygon_to_cells("geometry", 9))
    lazy = (
        frame.lazy().select("row", cells=plh3.polygon_to_cells("geometry", 9)).collect()
    )
    cells = eager["cells"].to_list()

    assert eager["row"].to_list() == [0, 1, 2, 3]
    assert cells[1] is None
    assert cells[2] == []
    assert set(cells[3]) == set(cells[0])
    assert len(cells[0]) == len(set(cells[0]))
    assert len(cells[3]) == len(set(cells[3]))
    assert lazy.equals(eager)


def test_polygon_to_cells_preserves_inferred_all_null_rows_eager_and_lazy():
    frame = pl.DataFrame({"geometry": [None, None]})

    eager = frame.select(cells=plh3.polygon_to_cells("geometry", 9))
    lazy = frame.lazy().select(cells=plh3.polygon_to_cells("geometry", 9)).collect()

    assert frame.schema["geometry"] == pl.Null
    assert eager.schema["cells"] == pl.List(pl.UInt64)
    assert eager["cells"].to_list() == [None, None]
    assert lazy.equals(eager)


@pytest.mark.parametrize("resolution", [-1, 16])
def test_polygon_wkt_to_cells_rejects_invalid_resolution(resolution: int):
    with pytest.raises(ValueError, match="Resolution must be between 0 and 15"):
        plh3.polygon_wkt_to_cells("wkt", resolution)


@pytest.mark.parametrize(
    "wkt,error",
    [
        ("not wkt", "Invalid WKT geometry"),
        ("POINT(-122.41 37.78)", "expected POLYGON or MULTIPOLYGON"),
    ],
)
def test_polygon_wkt_to_cells_rejects_invalid_geometry(wkt: str, error: str):
    with pytest.raises(pl.exceptions.ComputeError, match=error):
        _cells_for_wkt(wkt)


def test_polygon_wkt_to_cells_requires_string_input():
    with pytest.raises(
        pl.exceptions.ComputeError,
        match=r"expects a String \(WKT\) or Binary \(WKB\) column",
    ):
        pl.DataFrame({"geometry": [1]}).select(plh3.polygon_to_cells("geometry", 9))


def test_polygon_to_cells_rejects_invalid_wkb():
    frame = pl.DataFrame(
        {"geometry": [b"not wkb"]},
        schema={"geometry": pl.Binary},
    )

    with pytest.raises(pl.exceptions.ComputeError, match="Invalid WKB geometry"):
        frame.select(plh3.polygon_to_cells("geometry", 9))


@pytest.mark.parametrize(
    "wkt",
    [
        "POLYGON((0 91,1 91,1 92,0 92,0 91))",
        "POLYGON((181 0,182 0,182 1,181 1,181 0))",
    ],
)
def test_polygon_to_cells_rejects_out_of_range_wkt_coordinates(wkt: str):
    with pytest.raises(pl.exceptions.ComputeError, match="Invalid polygon coordinate"):
        _cells_for_wkt(wkt)


def test_polygon_to_cells_rejects_out_of_range_wkb_coordinates():
    wkb = _polygon_wkb(
        [[[0.0, 91.0], [1.0, 91.0], [1.0, 92.0], [0.0, 92.0], [0.0, 91.0]]]
    )
    frame = pl.DataFrame({"geometry": [wkb]}, schema={"geometry": pl.Binary})

    with pytest.raises(pl.exceptions.ComputeError, match="Invalid polygon coordinate"):
        frame.select(plh3.polygon_to_cells("geometry", 9))


@pytest.mark.parametrize("cell_dtype", [pl.UInt64, pl.Int64, pl.String])
def test_cells_to_multi_polygon_wkt_round_trip(cell_dtype: pl.DataType):
    original = _cells_for_wkt(POLYGON_WKT)
    if cell_dtype == pl.String:
        values = [h3.int_to_str(cell) for cell in original]
    else:
        values = original
    frame = pl.DataFrame(
        {"cells": [values]},
        schema={"cells": pl.List(cell_dtype)},
    )

    wkt = frame.select(plh3.cells_to_multi_polygon_wkt("cells")).item()
    round_trip = _cells_for_wkt(wkt)

    assert wkt.startswith("MULTIPOLYGON(")
    assert set(round_trip) == set(original)


def test_cells_to_multi_polygon_wkt_handles_empty_and_null_rows():
    frame = pl.DataFrame(
        {"cells": [[], None]},
        schema={"cells": pl.List(pl.UInt64)},
    )

    result = frame.select(wkt=plh3.cells_to_multi_polygon_wkt("cells"))

    assert result["wkt"].to_list() == ["MULTIPOLYGON EMPTY", None]


def test_cells_to_multi_polygon_wkt_handles_inferred_empty_list():
    frame = pl.DataFrame({"cells": [[]]})

    result = frame.select(wkt=plh3.cells_to_multi_polygon_wkt("cells"))

    assert frame.schema["cells"] == pl.List(pl.Null)
    assert result.item() == "MULTIPOLYGON EMPTY"


def test_cells_to_multi_polygon_wkt_preserves_inferred_all_null_rows():
    frame = pl.DataFrame({"cells": [None, None]})

    eager = frame.select(wkt=plh3.cells_to_multi_polygon_wkt("cells"))
    lazy = frame.lazy().select(wkt=plh3.cells_to_multi_polygon_wkt("cells")).collect()

    assert frame.schema["cells"] == pl.Null
    assert eager.schema["wkt"] == pl.String
    assert eager["wkt"].to_list() == [None, None]
    assert lazy.equals(eager)


def test_cells_to_multi_polygon_wkt_rejects_inferred_null_element():
    frame = pl.DataFrame({"cells": [[None]]})

    with pytest.raises(pl.exceptions.ComputeError, match="Null H3 cell"):
        frame.select(plh3.cells_to_multi_polygon_wkt("cells"))


def test_cells_to_multi_polygon_wkt_rejects_duplicates():
    cell = _cells_for_wkt(POLYGON_WKT)[0]
    frame = pl.DataFrame(
        {"cells": [[cell, cell]]},
        schema={"cells": pl.List(pl.UInt64)},
    )

    with pytest.raises(pl.exceptions.ComputeError, match="Cannot dissolve H3 cell set"):
        frame.select(plh3.cells_to_multi_polygon_wkt("cells"))


def test_cells_to_multi_polygon_wkt_rejects_mixed_resolutions():
    cell = _cells_for_wkt(POLYGON_WKT)[0]
    parent = h3.str_to_int(h3.cell_to_parent(h3.int_to_str(cell), 8))
    frame = pl.DataFrame(
        {"cells": [[cell, parent]]},
        schema={"cells": pl.List(pl.UInt64)},
    )

    with pytest.raises(pl.exceptions.ComputeError, match="Cannot dissolve H3 cell set"):
        frame.select(plh3.cells_to_multi_polygon_wkt("cells"))


def test_cells_to_multi_polygon_wkt_rejects_invalid_cells():
    frame = pl.DataFrame(
        {"cells": [[1]]},
        schema={"cells": pl.List(pl.UInt64)},
    )

    with pytest.raises(pl.exceptions.ComputeError, match="Invalid H3 cell"):
        frame.select(plh3.cells_to_multi_polygon_wkt("cells"))


def test_cells_to_multi_polygon_wkt_requires_list_input():
    with pytest.raises(pl.exceptions.ComputeError, match="expects a List column"):
        pl.DataFrame({"cells": [h3.latlng_to_cell(37.78, -122.41, 9)]}).select(
            plh3.cells_to_multi_polygon_wkt("cells")
        )
