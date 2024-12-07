use h3o::CellIndex;
use polars::prelude::*;
use rayon::prelude::*;

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

pub fn get_pentagons(resolution: u8) -> PolarsResult<Series> {
    let pentagons: Vec<u64> = h3o::Resolution::try_from(resolution)
        .map(|res| res.pentagons().map(|cell| cell.into()).collect())
        .map_err(|e| PolarsError::ComputeError(format!("Error getting pentagons: {}", e).into()))?;

    Ok(Series::new(PlSmallStr::from(""), pentagons))
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

// Can't figure out how to get the directed edge indices from a series
// pub fn edge_length(series: &Series, unit: &str) -> PolarsResult<Series> {
//     if unit != "km" && unit != "m" {
//         return Err(PolarsError::ComputeError(
//             "Invalid unit. Expected 'km' or 'm'.".into(),
//         ));
//     }

//     let edges = parse_directed_edge_indices(series)?;

//     let lengths: Float64Chunked = edges
//         .into_par_iter()
//         .map(|edge_opt| {
//             edge_opt.map(|edge| {
//                 let length_km = edge.length_km();
//                 match unit {
//                     "km" => length_km,
//                     "m" => length_km * 1000.0,
//                     _ => unreachable!(),
//                 }
//             })
//         })
//         .collect();

//     Ok(lengths.into_series())
// }
