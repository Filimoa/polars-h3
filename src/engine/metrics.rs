use h3o::{CellIndex, DirectedEdgeIndex, Resolution};
use polars::prelude::*;

use super::utils::{map_cells, map_indices};

pub fn get_num_cells_series(resolution_series: &Series) -> PolarsResult<Series> {
    let resolutions: Vec<Option<u8>> = match resolution_series.dtype() {
        DataType::UInt8 => resolution_series.u8()?.iter().collect(),
        DataType::UInt16 => resolution_series
            .u16()?
            .iter()
            .map(|opt| opt.and_then(|v| v.try_into().ok()))
            .collect(),
        DataType::UInt32 => resolution_series
            .u32()?
            .iter()
            .map(|opt| opt.and_then(|v| v.try_into().ok()))
            .collect(),
        DataType::UInt64 => resolution_series
            .u64()?
            .iter()
            .map(|opt| opt.and_then(|v| v.try_into().ok()))
            .collect(),
        DataType::Int8 => resolution_series
            .i8()?
            .iter()
            .map(|opt| opt.and_then(|v| if v >= 0 { Some(v as u8) } else { None }))
            .collect(),
        DataType::Int16 => resolution_series
            .i16()?
            .iter()
            .map(|opt| opt.and_then(|v| if v >= 0 { v.try_into().ok() } else { None }))
            .collect(),
        DataType::Int32 => resolution_series
            .i32()?
            .iter()
            .map(|opt| opt.and_then(|v| if v >= 0 { v.try_into().ok() } else { None }))
            .collect(),
        DataType::Int64 => resolution_series
            .i64()?
            .iter()
            .map(|opt| opt.and_then(|v| if v >= 0 { v.try_into().ok() } else { None }))
            .collect(),
        _ => {
            return Err(PolarsError::ComputeError(
                "Resolution must be an integer type".into(),
            ))
        },
    };

    // Compute the cell count for each valid resolution
    let counts: Vec<Option<u64>> = resolutions
        .into_iter()
        .map(|opt_res| {
            opt_res.and_then(|res| {
                h3o::Resolution::try_from(res) // Convert to H3 Resolution (0–15)
                    .ok() // Returns None if out of range
                    .map(|r| r.cell_count()) // Compute cell count
            })
        })
        .collect();

    // Return a Series of type UInt64 with the results
    Ok(
        UInt64Chunked::from_iter_options(PlSmallStr::from("count"), counts.into_iter())
            .into_series(),
    )
}

pub fn get_num_cells(resolution: u8) -> PolarsResult<Series> {
    let count = h3o::Resolution::try_from(resolution)
        .map(|res| res.cell_count())
        .map_err(|e| PolarsError::ComputeError(format!("Invalid resolution: {}", e).into()))?;

    Ok(Series::new(PlSmallStr::from(""), &[count]))
}

pub fn get_res0_cells() -> PolarsResult<Series> {
    let cells: Vec<u64> = CellIndex::base_cells().map(|cell| cell.into()).collect();

    Ok(Series::new(PlSmallStr::from(""), cells))
}

pub fn get_pentagons(inputs: &[Series]) -> PolarsResult<Series> {
    let resolutions: Vec<Option<u8>> = match inputs[0].dtype() {
        DataType::UInt8 => Ok::<_, PolarsError>(inputs[0].u8()?.iter().collect()),
        DataType::UInt16 => Ok::<_, PolarsError>(
            inputs[0]
                .u16()?
                .iter()
                .map(|opt| {
                    opt.map(|v| {
                        u8::try_from(v)
                            .map_err(|_| polars_err!(ComputeError: "Invalid resolution: {}", v))
                    })
                    .transpose()
                })
                .collect::<PolarsResult<_>>()?,
        ),
        DataType::UInt32 => Ok::<_, PolarsError>(
            inputs[0]
                .u32()?
                .iter()
                .map(|opt| {
                    opt.map(|v| {
                        u8::try_from(v)
                            .map_err(|_| polars_err!(ComputeError: "Invalid resolution: {}", v))
                    })
                    .transpose()
                })
                .collect::<PolarsResult<_>>()?,
        ),
        DataType::UInt64 => Ok::<_, PolarsError>(
            inputs[0]
                .u64()?
                .iter()
                .map(|opt| {
                    opt.map(|v| {
                        u8::try_from(v)
                            .map_err(|_| polars_err!(ComputeError: "Invalid resolution: {}", v))
                    })
                    .transpose()
                })
                .collect::<PolarsResult<_>>()?,
        ),
        DataType::Int64 => Ok::<_, PolarsError>(
            inputs[0]
                .i64()?
                .iter()
                .map(|opt| {
                    opt.map(|v| {
                        u8::try_from(v)
                            .map_err(|_| polars_err!(ComputeError: "Invalid resolution: {}", v))
                    })
                    .transpose()
                })
                .collect::<PolarsResult<_>>()?,
        ),
        _ => polars_bail!(ComputeError: "Expected an integer dtype for resolutions"),
    }?;

    let pentagons_by_res: Vec<Vec<u64>> = (0u8..=15)
        .map(|res| {
            Resolution::try_from(res)
                .expect("0..=15 are valid H3 resolutions")
                .pentagons()
                .map(Into::into)
                .collect()
        })
        .collect();

    let mut builder = ListPrimitiveChunkedBuilder::<UInt64Type>::new(
        PlSmallStr::from("pentagons"),
        resolutions.len(),
        resolutions.len() * 12,
        DataType::UInt64,
    );

    for res_opt in resolutions {
        match res_opt {
            Some(res) => {
                let pentagons = pentagons_by_res.get(res as usize).ok_or_else(|| {
                    PolarsError::ComputeError(format!("Invalid resolution: {}", res).into())
                })?;
                builder.append_slice(pentagons);
            },
            None => {
                builder.append_null();
            },
        }
    }

    Ok(builder.finish().into_series())
}

pub fn cell_area(cell_series: &Series, unit: &str) -> PolarsResult<Series> {
    map_cells::<Float64Type, _, _>(cell_series, |cell| {
        cell.and_then(|idx| {
            let area_km2 = idx.area_km2();
            match unit {
                "km^2" => Some(area_km2),
                "m^2" => Some(area_km2 * 1_000_000.0),
                _ => None, // invalid unit
            }
        })
    })
}

pub fn edge_length(series: &Series, unit: &str) -> PolarsResult<Series> {
    // Validate the unit
    if unit != "km" && unit != "m" {
        return Err(PolarsError::ComputeError(
            "Invalid unit. Expected 'km' or 'm'.".into(),
        ));
    }

    if !matches!(
        series.dtype(),
        DataType::UInt64 | DataType::Int64 | DataType::String
    ) {
        polars_bail!(ComputeError: "Expected String, UInt64, or Int64 for edge indices");
    }
    map_indices::<DirectedEdgeIndex, Float64Type, _, _>(series, "edge", |edge_opt| {
        edge_opt.map(|edge| {
            let length_km = edge.length_km(); // Get length in kilometers
            match unit {
                "km" => length_km,
                "m" => length_km * 1000.0, // Convert to meters
                _ => unreachable!(),       // Unit validation ensures this won't happen
            }
        })
    })
}
