use h3o::{CellIndex, LatLng, Resolution};
use polars::prelude::*;
use rayon::prelude::*;

use super::utils::parse_cell_indices;

fn parse_latlng_to_cells(
    lat_series: &Series,
    lng_series: &Series,
    resolution: u8,
) -> PolarsResult<Vec<Option<CellIndex>>> {
    let lat_vals = match lat_series.dtype() {
        DataType::Float64 => lat_series.f64()?.into_iter().collect::<Vec<_>>(),
        DataType::Float32 => {
            let lat_casted = lat_series.cast(&DataType::Float64)?;
            lat_casted.f64()?.into_iter().collect::<Vec<_>>()
        },
        _ => {
            return Err(PolarsError::ComputeError(
                "lat column must be Float32 or Float64".into(),
            ))
        },
    };

    let lng_vals = match lng_series.dtype() {
        DataType::Float64 => lng_series.f64()?.into_iter().collect::<Vec<_>>(),
        DataType::Float32 => {
            let lng_casted = lng_series.cast(&DataType::Float64)?;
            lng_casted.f64()?.into_iter().collect::<Vec<_>>()
        },
        _ => {
            return Err(PolarsError::ComputeError(
                "lng column must be Float32 or Float64".into(),
            ))
        },
    };

    let resolution = Resolution::try_from(resolution)
        .map_err(|_| polars_err!(ComputeError: "Invalid resolution: {}", resolution))?;

    let cells: Vec<Option<CellIndex>> = lat_vals
        .into_par_iter()
        .zip(lng_vals.into_par_iter())
        .map(|(opt_lat, opt_lng)| match (opt_lat, opt_lng) {
            (Some(lat), Some(lng)) => LatLng::new(lat, lng)
                .ok()
                .map(|coord| coord.to_cell(resolution)),
            _ => None,
        })
        .collect();

    Ok(cells)
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
