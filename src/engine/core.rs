use h3o::{LatLng, Resolution};
use polars::prelude::*;
use rayon::prelude::*;

pub fn latlng_to_cell(inputs: &[Series]) -> PolarsResult<Series> {
    let lat_ca = inputs[0].f64()?;
    let lng_ca = inputs[1].f64()?;
    let resolution = inputs[2].i32()?;
    let res = Resolution::try_from(resolution.get(0).unwrap_or(9))
        .map_err(|_| PolarsError::ComputeError("Invalid resolution".into()))?;

    let out: UInt64Chunked = (0..lat_ca.len())
        .into_par_iter()
        .map(|i| match (lat_ca.get(i), lng_ca.get(i)) {
            (Some(lat), Some(lng)) => LatLng::new(lat, lng)
                .ok()
                .map(|coord| coord.to_cell(res).into()),
            _ => None,
        })
        .collect();

    Ok(out.into_series())
}

pub fn latlng_to_cell_string(inputs: &[Series]) -> PolarsResult<Series> {
    let lat_ca = inputs[0].f64()?;
    let lng_ca = inputs[1].f64()?;
    let resolution = inputs[2].i32()?;

    let iter = lat_ca.into_iter().zip(lng_ca.into_iter());

    let out: StringChunked = iter
        .map(|(lat_opt, lng_opt)| match (lat_opt, lng_opt) {
            (Some(lat), Some(lng)) => LatLng::new(lat, lng).ok().and_then(|coord| {
                Resolution::try_from(resolution.get(0).unwrap_or(9))
                    .ok()
                    .map(|res| coord.to_cell(res).to_string())
            }),
            _ => None,
        })
        .collect();

    Ok(out.into_series())
}
