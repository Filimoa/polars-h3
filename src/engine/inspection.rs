use super::utils::parse_cell_indices;
use h3o::{CellIndex, LatLng, Resolution};
use polars::prelude::*;
use rayon::prelude::*;

pub fn get_resolution(cell_series: &Series) -> PolarsResult<Series> {
    // Convert input to u64 regardless of input type
    let cells = parse_cell_indices(cell_series)?;

    let resolutions: UInt32Chunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.and_then(|c| {
                CellIndex::try_from(c)
                    .ok()
                    .map(|idx| u8::from(idx.resolution()) as u32)
            })
        })
        .collect();

    Ok(resolutions.into_series())
}
