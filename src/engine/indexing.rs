use super::utils::parse_cell_indices;
use h3o::{CellIndex, LatLng, Resolution};
use polars::prelude::*;
use rayon::prelude::*;

fn parse_latlng_to_cells(
    lat_series: &Series,
    lng_series: &Series,
    resolution: u8,
) -> PolarsResult<Vec<Option<CellIndex>>> {
    let lat_ca = lat_series.f64()?;
    let lng_ca = lng_series.f64()?;
    let res = Resolution::try_from(resolution).map_err(|_| {
        PolarsError::ComputeError(format!("Invalid resolution: {}", resolution).into())
    })?;

    Ok((0..lat_ca.len())
        .into_par_iter()
        .map(|i| match (lat_ca.get(i), lng_ca.get(i)) {
            (Some(lat), Some(lng)) => LatLng::new(lat, lng).map(|coord| coord.to_cell(res)).ok(),
            _ => None,
        })
        .collect())
}

pub fn latlng_to_cell(
    lat_series: &Series,
    lng_series: &Series,
    resolution: u8,
) -> PolarsResult<Series> {
    let cells = parse_latlng_to_cells(lat_series, lng_series, resolution)?;

    let h3_indices: UInt64Chunked = cells
        .into_par_iter()
        .map(|cell| cell.map(Into::into))
        .collect();

    Ok(h3_indices.into_series())
}

pub fn latlng_to_cell_string(
    lat_series: &Series,
    lng_series: &Series,
    resolution: u8,
) -> PolarsResult<Series> {
    let cells = parse_latlng_to_cells(lat_series, lng_series, resolution)?;

    let h3_strings: StringChunked = cells
        .into_par_iter()
        .map(|cell| cell.map(|idx| idx.to_string()))
        .collect();

    Ok(h3_strings.into_series())
}

pub fn cell_to_lat(cell_series: &Series) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let lats: Float64Chunked = cells
        .into_par_iter()
        .map(|cell| cell.map(|idx| LatLng::from(idx).lat()))
        .collect();

    Ok(lats.into_series())
}

pub fn cell_to_lng(cell_series: &Series) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let lngs: Float64Chunked = cells
        .into_par_iter()
        .map(|cell| cell.map(|idx| LatLng::from(idx).lng()))
        .collect();

    Ok(lngs.into_series())
}

pub fn cell_to_latlng(cell_series: &Series) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let coords: ListChunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.map(|idx| {
                let latlng = LatLng::from(idx);
                Series::new(PlSmallStr::from(""), &[latlng.lat(), latlng.lng()])
            })
        })
        .collect();

    Ok(coords.into_series())
}
