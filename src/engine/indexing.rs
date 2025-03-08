use h3o::{CellIndex, LatLng, Resolution};
use polars::prelude::*;
use rayon::prelude::*;

use super::utils::{parse_cell_indices, parse_multi_f64_columns};

fn parse_latlng_to_cells(
    lat_series: &Series,
    lng_series: &Series,
    resolution: u8,
) -> PolarsResult<Vec<Option<CellIndex>>> {
    let lat_ca = lat_series.f64()?;
    let lng_ca = lng_series.f64()?;
    let res = Resolution::try_from(resolution)
        .map_err(|_| PolarsError::ComputeError("Invalid resolution".into()))?;

    let cells: Vec<Option<CellIndex>> = lat_ca
        .into_iter()
        .zip(lng_ca.into_iter())
        .map(|(lat_opt, lng_opt)| match (lat_opt, lng_opt) {
            (Some(lat), Some(lng)) => LatLng::new(lat, lng).ok().map(|coord| coord.to_cell(res)),
            _ => None, // Null if either lat or lng is null
        })
        .collect();

    Ok(cells)
}

pub fn latlng_to_cell(
    lat_series: &Series,
    lng_series: &Series,
    resolution: u8,
) -> PolarsResult<Series> {
    let lat_series = match lat_series.dtype() {
        DataType::Float64 | DataType::Null => lat_series.clone(),
        DataType::Float32 => lat_series.cast(&DataType::Float64)?,
        _ => {
            return Err(PolarsError::ComputeError(
                "lat column must be Float32 or Float64".into(),
            ));
        },
    };
    let lng_series = match lng_series.dtype() {
        DataType::Float64 | DataType::Null => lng_series.clone(),
        DataType::Float32 => lng_series.cast(&DataType::Float64)?,
        _ => {
            return Err(PolarsError::ComputeError(
                "lng column must be Float32 or Float64".into(),
            ));
        },
    };

    let lat_ca = lat_series.f64()?;
    let lng_ca = lng_series.f64()?;

    let res = Resolution::try_from(resolution).map_err(|_| {
        PolarsError::ComputeError(format!("Invalid resolution: {resolution}").into())
    })?;

    let lat_iter = lat_ca.into_iter();
    let lng_iter = lng_ca.into_iter();

    // Collect row-by-row into Vec<Option<u64>>
    let cells: Vec<Option<u64>> = lat_iter
        .zip(lng_iter)
        .map(|(opt_lat, opt_lng)| match (opt_lat, opt_lng) {
            (Some(lat), Some(lng)) => {
                // If lat/lng out-of-range => LatLng::new(...) returns Err => produce None.
                match LatLng::new(lat, lng) {
                    Ok(coord) => Some(coord.to_cell(res).into()),
                    Err(_) => None,
                }
            },
            // If either lat or lng is null => entire row is null
            _ => None,
        })
        .collect();

    let h3_indices: UInt64Chunked = cells.into_par_iter().collect();

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

pub fn cell_to_boundary(cell_series: &Series) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let coords: ListChunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.map(|idx| {
                let boundary = idx.boundary();

                // Create a Vec<Vec<f64>> for the boundary: each inner vec is [lat, lng]
                let latlng_pairs: Vec<Vec<f64>> = boundary
                    .iter()
                    .map(|vertex| vec![vertex.lat(), vertex.lng()])
                    .collect();

                // Convert each [lat, lng] pair into its own Series
                let inner_series: Vec<Series> = latlng_pairs
                    .into_iter()
                    .map(|coords| Series::new(PlSmallStr::from(""), coords))
                    .collect();

                Series::new(PlSmallStr::from(""), inner_series)
            })
        })
        .collect();

    Ok(coords.into_series())
}
