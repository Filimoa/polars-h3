use super::utils::parse_cell_indices;
use h3o::{CellIndex, Resolution};
use polars::prelude::*;
use rayon::prelude::*;

const EARTH_RADIUS_KM: f64 = 6371.007180918475;

pub fn cell_area(cell_series: &Series, unit: &str) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let areas: Float64Chunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.map(|idx| {
                let area_rads2 = idx.area_rads2();
                match unit {
                    "rads^2" => area_rads2,
                    "km^2" => area_rads2 * EARTH_RADIUS_KM * EARTH_RADIUS_KM,
                    "m^2" => area_rads2 * EARTH_RADIUS_KM * EARTH_RADIUS_KM * 1_000_000.0,
                    _ => f64::NAN,
                }
            })
        })
        .collect();

    Ok(areas.into_series())
}

// Cell counting functions
pub fn get_num_cells(resolution: u8) -> PolarsResult<Series> {
    let res = Resolution::try_from(resolution)
        .map_err(|_| PolarsError::ComputeError("Invalid resolution".into()))?;

    let num_cells = 2 + 120 * (7_u64.pow(u32::from(resolution)));
    Ok(Series::new(PlSmallStr::from(""), &[num_cells]))
}

pub fn get_res0_cells() -> PolarsResult<Series> {
    let cells: ListChunked = vec![Some(Series::new(
        PlSmallStr::from(""),
        CellIndex::base_cells()
            .map(u64::from)
            .collect::<Vec<_>>()
            .as_slice(),
    ))]
    .into_iter()
    .collect();

    Ok(cells.into_series())
}

pub fn get_pentagons(resolution: u8) -> PolarsResult<Series> {
    let res = Resolution::try_from(resolution)
        .map_err(|_| PolarsError::ComputeError("Invalid resolution".into()))?;

    let pentagons: ListChunked = vec![Some(Series::new(
        PlSmallStr::from(""),
        CellIndex::base_cells()
            .filter(|cell| cell.is_pentagon())
            .map(|cell| u64::from(cell.center_child(res).unwrap_or(cell)))
            .collect::<Vec<_>>()
            .as_slice(),
    ))]
    .into_iter()
    .collect();

    Ok(pentagons.into_series())
}
