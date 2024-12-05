use h3o::{CellIndex, LatLng, Resolution};
use polars::prelude::*;

pub fn latlng_to_cell(inputs: &[Series]) -> PolarsResult<Series> {
    let lat_ca = inputs[0].f64()?;
    let lng_ca = inputs[1].f64()?;
    let resolution = inputs[2].i32()?;

    let iter = lat_ca.into_iter().zip(lng_ca.into_iter());

    let out: UInt64Chunked = iter
        .map(|(lat_opt, lng_opt)| match (lat_opt, lng_opt) {
            (Some(lat), Some(lng)) => LatLng::new(lat, lng).ok().and_then(|coord| {
                Resolution::try_from(resolution.get(0).unwrap_or(9))
                    .ok()
                    .map(|res| coord.to_cell(res).into())
            }),
            _ => None,
        })
        .collect();

    Ok(out.into_series())
}

// pub fn latlng_to_cell_string(inputs: &[Series], resolution: u8) -> PolarsResult<Series> {
//     let lat_ca = inputs[0].f64()?;
//     let lng_ca = inputs[1].f64()?;

//     let iter = lat_ca.into_iter().zip(lng_ca.into_iter());

//     let out: StringChunked = iter
//         .map(|(lat_opt, lng_opt)| match (lat_opt, lng_opt) {
//             (Some(lat), Some(lng)) => LatLng::new(lat, lng).ok().and_then(|coord| {
//                 Resolution::try_from(resolution)
//                     .ok()
//                     .map(|res| coord.to_cell(res).to_string())
//             }),
//             _ => None,
//         })
//         .collect();

//     Ok(out.into_series())
// }
