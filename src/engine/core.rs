use h3o::{LatLng, Resolution};
use polars::prelude::*;
use rayon::prelude::*;

pub fn latlng_to_cell(
    lat_series: &Series,
    lng_series: &Series,
    resolution: u8,
) -> PolarsResult<Series> {
    let lat_ca = lat_series.f64()?;
    let lng_ca = lng_series.f64()?;
    let res = Resolution::try_from(resolution).map_err(|_| {
        PolarsError::ComputeError(format!("Invalid resolution: {}", resolution).into())
    })?;

    let h3_indices: UInt64Chunked = (0..lat_ca.len())
        .into_par_iter()
        .map(|i| match (lat_ca.get(i), lng_ca.get(i)) {
            (Some(lat), Some(lng)) => LatLng::new(lat, lng)
                .map(|coord| coord.to_cell(res).into())
                .ok(),
            _ => None,
        })
        .collect();

    Ok(h3_indices.into_series())
}

pub fn latlng_to_cell_string(
    lat_series: &Series,
    lng_series: &Series,
    resolution: u8,
) -> PolarsResult<Series> {
    let lat_ca = lat_series.f64()?;
    let lng_ca = lng_series.f64()?;
    let res = Resolution::try_from(resolution).map_err(|_| {
        PolarsError::ComputeError(format!("Invalid resolution: {}", resolution).into())
    })?;

    let h3_strings: StringChunked = (0..lat_ca.len())
        .into_par_iter()
        .map(|i| match (lat_ca.get(i), lng_ca.get(i)) {
            (Some(lat), Some(lng)) => LatLng::new(lat, lng)
                .ok()
                .map(|coord| coord.to_cell(res).to_string()),
            _ => None,
        })
        .collect();

    Ok(h3_strings.into_series())
}
