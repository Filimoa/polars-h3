use h3o::{CellIndex, DirectedEdgeIndex, Resolution};
use polars::prelude::*;

use super::utils::{map_cells, map_indices, parallel_chunks};

pub fn get_num_cells_series(resolution_series: &Series) -> PolarsResult<Series> {
    parallel_chunks(resolution_series.len(), |offset, len| {
        let slice = resolution_series.slice(offset as i64, len);
        macro_rules! counts {
            ($values:expr) => {
                $values
                    .iter()
                    .map(|value| {
                        value
                            .and_then(|v| u8::try_from(v).ok())
                            .and_then(|v| Resolution::try_from(v).ok())
                            .map(|resolution| resolution.cell_count())
                    })
                    .collect::<UInt64Chunked>()
            };
        }
        let counts = match slice.dtype() {
            DataType::UInt8 => counts!(slice.u8()?),
            DataType::UInt16 => counts!(slice.u16()?),
            DataType::UInt32 => counts!(slice.u32()?),
            DataType::UInt64 => counts!(slice.u64()?),
            DataType::Int8 => counts!(slice.i8()?),
            DataType::Int16 => counts!(slice.i16()?),
            DataType::Int32 => counts!(slice.i32()?),
            DataType::Int64 => counts!(slice.i64()?),
            _ => polars_bail!(ComputeError: "Resolution must be an integer type"),
        };
        Ok(counts
            .with_name(PlSmallStr::from_static("count"))
            .into_series())
    })
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

    // Preserve first-invalid-resolution errors before dispatching output batches.
    for &res in resolutions.iter().flatten() {
        if res > 15 {
            polars_bail!(ComputeError: "Invalid resolution: {}", res);
        }
    }
    parallel_chunks(resolutions.len(), |offset, len| {
        let mut builder = ListPrimitiveChunkedBuilder::<UInt64Type>::new(
            PlSmallStr::from_static("pentagons"),
            len,
            len * 12,
            DataType::UInt64,
        );
        for &resolution in &resolutions[offset..offset + len] {
            match resolution {
                Some(resolution) => builder.append_slice(&pentagons_by_res[resolution as usize]),
                None => builder.append_null(),
            }
        }
        Ok(builder.finish().into_series())
    })
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
