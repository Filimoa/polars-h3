use geo::{Geometry, Polygon};
use geozero::{
    wkb::{Ewkb, Wkb},
    ToGeo, ToJson,
};
use h3o::{
    geom::{SolventBuilder, TilerBuilder},
    CellIndex, Resolution,
};
use polars::prelude::*;
use rayon::prelude::*;
use wkt::{ToWkt, Wkt};

use super::utils::list_u64_vecs_to_series;

fn ensure_polygon(geometry: &Geometry<f64>) -> PolarsResult<()> {
    match geometry {
        Geometry::Polygon(_) | Geometry::MultiPolygon(_) => Ok(()),
        geometry => polars_bail!(
            ComputeError:
            "Unsupported geometry type: expected POLYGON or MULTIPOLYGON, got {}",
            geometry_type_name(geometry)
        ),
    }
}

fn validate_polygon_coordinates(polygon: &Polygon<f64>) -> PolarsResult<()> {
    for (ring_index, ring) in std::iter::once(polygon.exterior())
        .chain(polygon.interiors().iter())
        .enumerate()
    {
        for (position, coordinate) in ring.0.iter().enumerate() {
            if !coordinate.x.is_finite()
                || !coordinate.y.is_finite()
                || !(-180.0..=180.0).contains(&coordinate.x)
                || !(-90.0..=90.0).contains(&coordinate.y)
            {
                polars_bail!(
                    ComputeError:
                    "Invalid polygon coordinate at ring {}, position {}: longitude {} must be between -180 and 180 and latitude {} must be between -90 and 90",
                    ring_index,
                    position,
                    coordinate.x,
                    coordinate.y
                );
            }
        }
    }
    Ok(())
}

fn validate_geometry(geometry: &Geometry<f64>) -> PolarsResult<()> {
    ensure_polygon(geometry)?;
    match geometry {
        Geometry::Polygon(polygon) => validate_polygon_coordinates(polygon),
        Geometry::MultiPolygon(multi_polygon) => multi_polygon
            .0
            .iter()
            .try_for_each(validate_polygon_coordinates),
        _ => unreachable!("geometry type checked above"),
    }
}

fn polygon_is_empty(polygon: &Polygon<f64>) -> bool {
    polygon.exterior().0.is_empty() && polygon.interiors().iter().all(|ring| ring.0.is_empty())
}

fn validate_wkt_polygon(polygon: &wkt::types::Polygon<f64>) -> PolarsResult<()> {
    for (ring_index, ring) in polygon.rings().iter().enumerate() {
        let coordinates = ring.coords();
        if coordinates.len() < 4 {
            polars_bail!(
                ComputeError:
                "Invalid WKT geometry: ring {} has {} coordinates; expected at least 4",
                ring_index,
                coordinates.len()
            );
        }
        let first = coordinates.first().expect("non-empty ring checked above");
        let last = coordinates.last().expect("non-empty ring checked above");
        if first.x != last.x || first.y != last.y {
            polars_bail!(
                ComputeError:
                "Invalid WKT geometry: ring {} is not closed",
                ring_index
            );
        }
    }
    Ok(())
}

#[derive(Clone, Copy)]
enum WkbByteOrder {
    BigEndian,
    LittleEndian,
}

#[derive(Clone, Copy)]
enum BinaryGeometryDialect {
    Wkb,
    Ewkb,
}

struct StrictWkbReader<'a> {
    bytes: &'a [u8],
    offset: usize,
    dialect: Option<BinaryGeometryDialect>,
}

impl<'a> StrictWkbReader<'a> {
    fn new(bytes: &'a [u8]) -> Self {
        Self {
            bytes,
            offset: 0,
            dialect: None,
        }
    }

    fn remaining(&self) -> usize {
        self.bytes.len().saturating_sub(self.offset)
    }

    fn read_array<const N: usize>(&mut self) -> PolarsResult<[u8; N]> {
        let end = self
            .offset
            .checked_add(N)
            .ok_or_else(|| polars_err!(ComputeError: "Invalid WKB geometry: size overflow"))?;
        let bytes = self
            .bytes
            .get(self.offset..end)
            .ok_or_else(|| polars_err!(ComputeError: "Invalid WKB geometry: truncated payload"))?;
        self.offset = end;
        Ok(bytes.try_into().expect("slice length checked above"))
    }

    fn read_byte_order(&mut self) -> PolarsResult<WkbByteOrder> {
        let marker = self.read_array::<1>()?[0];
        match marker {
            0 => Ok(WkbByteOrder::BigEndian),
            1 => Ok(WkbByteOrder::LittleEndian),
            _ => polars_bail!(
                ComputeError:
                "Invalid WKB geometry: byte-order marker must be 0 or 1, got {}",
                marker
            ),
        }
    }

    fn read_u32(&mut self, byte_order: WkbByteOrder) -> PolarsResult<u32> {
        let bytes = self.read_array::<4>()?;
        Ok(match byte_order {
            WkbByteOrder::BigEndian => u32::from_be_bytes(bytes),
            WkbByteOrder::LittleEndian => u32::from_le_bytes(bytes),
        })
    }

    fn read_f64(&mut self, byte_order: WkbByteOrder) -> PolarsResult<f64> {
        let bytes = self.read_array::<8>()?;
        Ok(match byte_order {
            WkbByteOrder::BigEndian => f64::from_be_bytes(bytes),
            WkbByteOrder::LittleEndian => f64::from_le_bytes(bytes),
        })
    }

    fn read_header(&mut self) -> PolarsResult<(WkbByteOrder, u32, usize)> {
        let byte_order = self.read_byte_order()?;
        let type_id = self.read_u32(byte_order)?;
        let has_ewkb_flags = type_id & 0xe000_0000 != 0;
        let dialect = *self.dialect.get_or_insert(if has_ewkb_flags {
            BinaryGeometryDialect::Ewkb
        } else {
            BinaryGeometryDialect::Wkb
        });

        match dialect {
            BinaryGeometryDialect::Ewkb => {
                if type_id & 0x1fff_ff00 != 0 {
                    polars_bail!(
                        ComputeError:
                        "Invalid EWKB geometry: unsupported type id {}",
                        type_id
                    );
                }
                let dimensions = 2
                    + usize::from(type_id & 0x8000_0000 != 0)
                    + usize::from(type_id & 0x4000_0000 != 0);
                if type_id & 0x2000_0000 != 0 {
                    let srid = self.read_u32(byte_order)?;
                    if srid != 4326 {
                        polars_bail!(
                            ComputeError:
                            "Invalid EWKB geometry: expected SRID 4326, got {}",
                            srid
                        );
                    }
                }
                Ok((byte_order, type_id & 0xff, dimensions))
            },
            BinaryGeometryDialect::Wkb => {
                if has_ewkb_flags {
                    polars_bail!(
                        ComputeError:
                        "Invalid WKB geometry: EWKB flags are not valid inside standard WKB"
                    );
                }
                let dimension_code = type_id / 1000;
                if dimension_code > 3 {
                    polars_bail!(
                        ComputeError:
                        "Invalid WKB geometry: unsupported dimensional type id {}",
                        type_id
                    );
                }
                let dimensions = match dimension_code {
                    0 => 2,
                    1 | 2 => 3,
                    3 => 4,
                    _ => unreachable!("dimension code bounded above"),
                };
                Ok((byte_order, type_id % 1000, dimensions))
            },
        }
    }

    fn read_polygon(&mut self, byte_order: WkbByteOrder, dimensions: usize) -> PolarsResult<()> {
        let ring_count = self.read_u32(byte_order)? as usize;
        if ring_count > self.remaining() / 4 {
            polars_bail!(ComputeError: "Invalid WKB geometry: truncated polygon rings");
        }

        for ring_index in 0..ring_count {
            let point_count = self.read_u32(byte_order)? as usize;
            if point_count < 4 {
                polars_bail!(
                    ComputeError:
                    "Invalid WKB geometry: ring {} has {} coordinates; expected at least 4",
                    ring_index,
                    point_count
                );
            }
            let coordinate_bytes = point_count
                .checked_mul(dimensions)
                .and_then(|count| count.checked_mul(8))
                .ok_or_else(|| polars_err!(ComputeError: "Invalid WKB geometry: size overflow"))?;
            if coordinate_bytes > self.remaining() {
                polars_bail!(ComputeError: "Invalid WKB geometry: truncated polygon ring");
            }

            let mut first = None;
            let mut last = None;
            for _ in 0..point_count {
                let x = self.read_f64(byte_order)?;
                let y = self.read_f64(byte_order)?;
                for _ in 2..dimensions {
                    self.read_f64(byte_order)?;
                }
                first.get_or_insert((x, y));
                last = Some((x, y));
            }
            if first != last {
                polars_bail!(
                    ComputeError:
                    "Invalid WKB geometry: ring {} is not closed",
                    ring_index
                );
            }
        }
        Ok(())
    }

    fn read_geometry(&mut self, expected_type: Option<u32>) -> PolarsResult<()> {
        let (byte_order, geometry_type, dimensions) = self.read_header()?;
        if let Some(expected_type) = expected_type {
            if geometry_type != expected_type {
                polars_bail!(
                    ComputeError:
                    "Invalid WKB geometry: expected nested Polygon type, got {}",
                    geometry_type
                );
            }
        }

        match geometry_type {
            3 => self.read_polygon(byte_order, dimensions),
            6 if expected_type.is_none() => {
                let polygon_count = self.read_u32(byte_order)? as usize;
                if polygon_count > self.remaining() / 9 {
                    polars_bail!(
                        ComputeError:
                        "Invalid WKB geometry: truncated multipolygon members"
                    );
                }
                for _ in 0..polygon_count {
                    self.read_geometry(Some(3))?;
                }
                Ok(())
            },
            _ => polars_bail!(
                ComputeError:
                "Invalid WKB geometry: expected Polygon or MultiPolygon type, got {}",
                geometry_type
            ),
        }
    }
}

fn validate_wkb_structure(value: &[u8]) -> PolarsResult<BinaryGeometryDialect> {
    let mut reader = StrictWkbReader::new(value);
    reader.read_geometry(None)?;
    if reader.remaining() != 0 {
        polars_bail!(
            ComputeError:
            "Invalid WKB geometry: {} trailing bytes",
            reader.remaining()
        );
    }
    Ok(reader
        .dialect
        .expect("a successfully parsed geometry always has a header"))
}

fn polygon_to_cells(geometry: Geometry<f64>, resolution: Resolution) -> PolarsResult<Vec<u64>> {
    validate_geometry(&geometry)?;
    let mut tiler = TilerBuilder::new(resolution).build();

    match geometry {
        Geometry::Polygon(polygon) if polygon_is_empty(&polygon) => Ok(()),
        Geometry::Polygon(polygon) => tiler.add(polygon),
        Geometry::MultiPolygon(multi_polygon) => tiler.add_batch(
            multi_polygon
                .0
                .into_iter()
                .filter(|polygon| !polygon_is_empty(polygon)),
        ),
        _ => unreachable!("geometry type checked above"),
    }
    .map_err(|error| polars_err!(ComputeError: "Invalid polygon geometry: {}", error))?;

    let mut cells = tiler.into_coverage().map(u64::from).collect::<Vec<_>>();
    cells.sort_unstable();
    cells.dedup();
    Ok(cells)
}

fn parse_wkt_geometry(value: &str) -> PolarsResult<Geometry<f64>> {
    let parsed = value
        .parse::<Wkt<f64>>()
        .map_err(|error| polars_err!(ComputeError: "Invalid WKT geometry: {}", error))?;
    match &parsed {
        Wkt::Polygon(polygon) => validate_wkt_polygon(polygon)?,
        Wkt::MultiPolygon(multi_polygon) => multi_polygon
            .polygons()
            .iter()
            .try_for_each(validate_wkt_polygon)?,
        _ => {},
    }
    Geometry::<f64>::try_from(parsed)
        .map_err(|error| polars_err!(ComputeError: "Invalid WKT geometry: {}", error))
}

fn parse_wkb_geometry(value: &[u8]) -> PolarsResult<Geometry<f64>> {
    let dialect = validate_wkb_structure(value)?;
    match dialect {
        BinaryGeometryDialect::Wkb => Wkb(value).to_geo(),
        BinaryGeometryDialect::Ewkb => Ewkb(value).to_geo(),
    }
    .map_err(|error| polars_err!(ComputeError: "Invalid WKB geometry: {}", error))
}

fn polygon_to_geojson(mut geometry: Geometry<f64>) -> PolarsResult<String> {
    validate_geometry(&geometry)?;
    match &mut geometry {
        Geometry::Polygon(polygon) if polygon_is_empty(polygon) => {
            return Ok(r#"{"type":"Polygon","coordinates":[]}"#.to_string());
        },
        Geometry::MultiPolygon(multi_polygon) => {
            multi_polygon.0.retain(|polygon| !polygon_is_empty(polygon));
        },
        _ => {},
    }
    geometry.to_json().map_err(
        |error| polars_err!(ComputeError: "Cannot serialize geometry as GeoJSON: {}", error),
    )
}

fn geometry_type_name(geometry: &Geometry<f64>) -> &'static str {
    match geometry {
        Geometry::Point(_) => "POINT",
        Geometry::Line(_) => "LINE",
        Geometry::LineString(_) => "LINESTRING",
        Geometry::Polygon(_) => "POLYGON",
        Geometry::MultiPoint(_) => "MULTIPOINT",
        Geometry::MultiLineString(_) => "MULTILINESTRING",
        Geometry::MultiPolygon(_) => "MULTIPOLYGON",
        Geometry::GeometryCollection(_) => "GEOMETRYCOLLECTION",
        Geometry::Rect(_) => "RECT",
        Geometry::Triangle(_) => "TRIANGLE",
    }
}

pub fn polygon_to_cells_series(geometry_series: &Series, resolution: u8) -> PolarsResult<Series> {
    let resolution = Resolution::try_from(resolution)
        .map_err(|_| polars_err!(ComputeError: "Invalid resolution: {}", resolution))?;
    let cells = match geometry_series.dtype() {
        DataType::Null => vec![None; geometry_series.len()],
        DataType::String => {
            let values = geometry_series.str()?.iter().collect::<Vec<_>>();
            values
                .into_par_iter()
                .map(|value| {
                    value
                        .map(|value| {
                            parse_wkt_geometry(value)
                                .and_then(|geometry| polygon_to_cells(geometry, resolution))
                        })
                        .transpose()
                })
                .collect::<PolarsResult<Vec<_>>>()?
        },
        DataType::Binary => {
            let values = geometry_series.binary()?.iter().collect::<Vec<_>>();
            values
                .into_par_iter()
                .map(|value| {
                    value
                        .map(|value| {
                            parse_wkb_geometry(value)
                                .and_then(|geometry| polygon_to_cells(geometry, resolution))
                        })
                        .transpose()
                })
                .collect::<PolarsResult<Vec<_>>>()?
        },
        dtype => {
            polars_bail!(
                ComputeError:
                "polygon_to_cells expects a String (WKT) or Binary (WKB) column, got {:?}",
                dtype
            )
        },
    };

    list_u64_vecs_to_series(geometry_series.name().clone(), cells, &DataType::UInt64)
}

pub fn polygon_to_geojson_series(geometry_series: &Series) -> PolarsResult<Series> {
    let geometries = match geometry_series.dtype() {
        DataType::Null => vec![None; geometry_series.len()],
        DataType::String => {
            let values = geometry_series.str()?.iter().collect::<Vec<_>>();
            values
                .into_par_iter()
                .map(|value| {
                    value
                        .map(|value| parse_wkt_geometry(value).and_then(polygon_to_geojson))
                        .transpose()
                })
                .collect::<PolarsResult<Vec<_>>>()?
        },
        DataType::Binary => {
            let values = geometry_series.binary()?.iter().collect::<Vec<_>>();
            values
                .into_par_iter()
                .map(|value| {
                    value
                        .map(|value| parse_wkb_geometry(value).and_then(polygon_to_geojson))
                        .transpose()
                })
                .collect::<PolarsResult<Vec<_>>>()?
        },
        dtype => {
            polars_bail!(
                ComputeError:
                "polygon_to_geojson expects a String (WKT) or Binary (WKB) column, got {:?}",
                dtype
            )
        },
    };

    let output: StringChunked = geometries.into_iter().collect();
    Ok(output
        .with_name(geometry_series.name().clone())
        .into_series())
}

fn parse_cells_strict(series: &Series) -> PolarsResult<Vec<CellIndex>> {
    match series.dtype() {
        DataType::Null if series.is_empty() => Ok(Vec::new()),
        DataType::Null => polars_bail!(
            ComputeError:
            "Null H3 cell at list position 0"
        ),
        DataType::UInt64 => series
            .u64()?
            .iter()
            .enumerate()
            .map(|(index, value)| {
                let value = value.ok_or_else(
                    || polars_err!(ComputeError: "Null H3 cell at list position {}", index),
                )?;
                CellIndex::try_from(value).map_err(|error| {
                    polars_err!(
                        ComputeError:
                        "Invalid H3 cell at list position {}: {}",
                        index,
                        error
                    )
                })
            })
            .collect(),
        DataType::Int64 => series
            .i64()?
            .iter()
            .enumerate()
            .map(|(index, value)| {
                let value = value.ok_or_else(
                    || polars_err!(ComputeError: "Null H3 cell at list position {}", index),
                )?;
                let value = u64::try_from(value).map_err(|_| {
                    polars_err!(
                        ComputeError:
                        "Invalid negative H3 cell at list position {}",
                        index
                    )
                })?;
                CellIndex::try_from(value).map_err(|error| {
                    polars_err!(
                        ComputeError:
                        "Invalid H3 cell at list position {}: {}",
                        index,
                        error
                    )
                })
            })
            .collect(),
        DataType::String => series
            .str()?
            .iter()
            .enumerate()
            .map(|(index, value)| {
                let value = value.ok_or_else(
                    || polars_err!(ComputeError: "Null H3 cell at list position {}", index),
                )?;
                let value = u64::from_str_radix(value, 16).map_err(|error| {
                    polars_err!(
                        ComputeError:
                        "Invalid H3 cell string at list position {}: {}",
                        index,
                        error
                    )
                })?;
                CellIndex::try_from(value).map_err(|error| {
                    polars_err!(
                        ComputeError:
                        "Invalid H3 cell at list position {}: {}",
                        index,
                        error
                    )
                })
            })
            .collect(),
        dtype => polars_bail!(
            ComputeError:
            "Unsupported H3 cell list dtype: {:?}; expected UInt64, Int64, or String",
            dtype
        ),
    }
}

fn cells_to_wkt(series: &Series) -> PolarsResult<String> {
    let cells = parse_cells_strict(series)?;
    let multi_polygon = SolventBuilder::new()
        .build()
        .dissolve(cells)
        .map_err(|error| polars_err!(ComputeError: "Cannot dissolve H3 cell set: {}", error))?;
    Ok(multi_polygon.wkt_string())
}

pub fn cells_to_multi_polygon_wkt(cell_series: &Series) -> PolarsResult<Series> {
    if matches!(cell_series.dtype(), DataType::Null) {
        return Ok(Series::full_null(
            cell_series.name().clone(),
            cell_series.len(),
            &DataType::String,
        ));
    }

    let lists = cell_series.list().map_err(|_| {
        polars_err!(
            ComputeError:
            "cells_to_multi_polygon_wkt expects a List column, got {:?}",
            cell_series.dtype()
        )
    })?;
    let rows = lists.series_iter().collect::<Vec<_>>();
    let wkts = rows
        .into_par_iter()
        .map(|row| row.map(|row| cells_to_wkt(&row)).transpose())
        .collect::<PolarsResult<Vec<_>>>()?;
    let output: StringChunked = wkts.into_iter().collect();

    Ok(output.with_name(cell_series.name().clone()).into_series())
}
