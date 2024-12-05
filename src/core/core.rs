use h3o::{CellIndex, LatLng, Resolution};
use polars::prelude::*;

pub fn lat_lng_to_h3(inputs: &[Series]) -> PolarsResult<Series> {
    // Expecting lat and lng columns as inputs
    let lat_ca = inputs[0].f64()?;
    let lng_ca = inputs[1].f64()?;

    // Create iterator over the lat/lng pairs
    let iter = lat_ca.into_iter().zip(lng_ca.into_iter());

    // Convert each pair to H3 cell
    let out: UInt64Chunked = iter
        .map(|(lat_opt, lng_opt)| match (lat_opt, lng_opt) {
            (Some(lat), Some(lng)) => LatLng::new(lat, lng)
                .ok()
                .map(|coord| coord.to_cell(Resolution::Nine).into()),
            _ => None,
        })
        .collect();

    Ok(out.into_series())
}
