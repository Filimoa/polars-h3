use h3o::{CellIndex, DirectedEdgeIndex, Resolution};
use polars::prelude::*;
use rayon::prelude::*;
use std::str::FromStr;

use super::utils::parse_cell_indices;

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
        DataType::UInt8 => Ok::<_, PolarsError>(inputs[0].u8()?.into_iter().collect()),
        DataType::Int64 => Ok::<_, PolarsError>(
            inputs[0]
                .i64()?
                .into_iter()
                .map(|opt| opt.map(|v| v as u8))
                .collect(),
        ),
        _ => polars_bail!(ComputeError: "Expected UInt8 or Int64 for resolutions"),
    }?;

    let mut builder = ListPrimitiveChunkedBuilder::<UInt64Type>::new(
        PlSmallStr::from("pentagons"),
        resolutions.len(),
        resolutions.len() * 12,
        DataType::UInt64,
    );

    for res_opt in resolutions {
        match res_opt {
            Some(res) => {
                let pentagons: Vec<u64> = Resolution::try_from(res)
                    .map_err(|e| {
                        PolarsError::ComputeError(format!("Error getting pentagons: {}", e).into())
                    })?
                    .pentagons()
                    .map(|cell| cell.into())
                    .collect();
                builder.append_slice(&pentagons);
            },
            None => {
                builder.append_null();
            },
        }
    }

    Ok(builder.finish().into_series())
}

pub fn cell_area(cell_series: &Series, unit: &str) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let areas: Float64Chunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.and_then(|idx| {
                let area_km2 = idx.area_km2();
                match unit {
                    "km^2" => Some(area_km2),
                    "m^2" => Some(area_km2 * 1_000_000.0),
                    _ => None, // invalid unit
                }
            })
        })
        .collect();

    Ok(areas.into_series())
}

pub fn edge_length(series: &Series, unit: &str) -> PolarsResult<Series> {
    // Validate the unit
    if unit != "km" && unit != "m" {
        return Err(PolarsError::ComputeError(
            "Invalid unit. Expected 'km' or 'm'.".into(),
        ));
    }

    // Parse the edge indices from the series
    let edges = parse_edge_indices(series)?;

    // Calculate lengths in parallel and convert to the requested unit
    let lengths: Float64Chunked = edges
        .into_par_iter()
        .map(|edge_opt| {
            edge_opt.map(|edge| {
                let length_km = edge.length_km(); // Get length in kilometers
                match unit {
                    "km" => length_km,
                    "m" => length_km * 1000.0, // Convert to meters
                    _ => unreachable!(),       // Unit validation ensures this won't happen
                }
            })
        })
        .collect();

    // Convert the chunked array into a series
    Ok(lengths.into_series())
}

fn parse_edge_indices(series: &Series) -> PolarsResult<Vec<Option<DirectedEdgeIndex>>> {
    match series.dtype() {
        // Handle string input (hexadecimal edge indices)
        DataType::String => {
            let ca = series.str()?;
            Ok(ca
                .into_iter()
                .map(|opt| opt.and_then(|s| DirectedEdgeIndex::from_str(s).ok()))
                .collect())
        },
        // Handle u64 input
        DataType::UInt64 => {
            let ca = series.u64()?;
            Ok(ca
                .into_iter()
                .map(|opt| opt.and_then(|v| DirectedEdgeIndex::try_from(v).ok()))
                .collect())
        },
        // Handle i64 input (only non-negative values are valid)
        DataType::Int64 => {
            let ca = series.i64()?;
            Ok(ca
                .into_iter()
                .map(|opt| {
                    opt.and_then(|v| {
                        if v >= 0 {
                            DirectedEdgeIndex::try_from(v as u64).ok()
                        } else {
                            None // Negative values are invalid
                        }
                    })
                })
                .collect())
        },
        _ => Err(PolarsError::ComputeError(
            "Expected String, UInt64, or Int64 for edge indices".into(),
        )),
    }
}
