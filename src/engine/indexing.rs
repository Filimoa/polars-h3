use h3o::{CellIndex, LatLng, Resolution};
use polars::prelude::*;
use rayon::prelude::*;

use super::utils::parse_cell_indices;
fn parse_latlng_to_cells(
    lat_series: &Series,
    lng_series: &Series,
    resolution: u8,
) -> PolarsResult<Vec<Option<CellIndex>>> {
    let lat_series = match lat_series.dtype() {
        DataType::Float64 => lat_series.clone(),
        DataType::Float32 => lat_series.cast(&DataType::Float64)?,
        _ => {
            return Err(PolarsError::ComputeError(
                "lat column must be Float32 or Float64".into(),
            ))
        },
    };
    let lng_series = match lng_series.dtype() {
        DataType::Float64 => lng_series.clone(),
        DataType::Float32 => lng_series.cast(&DataType::Float64)?,
        _ => {
            return Err(PolarsError::ComputeError(
                "lng column must be Float32 or Float64".into(),
            ))
        },
    };

    let lat_ca = lat_series.f64()?;
    let lng_ca = lng_series.f64()?;
    let res = Resolution::try_from(resolution).map_err(|_| {
        PolarsError::ComputeError(format!("Invalid resolution: {}", resolution).into())
    })?;

    let lat_values = lat_ca
        .cont_slice()
        .expect("No nulls expected in lat_series");
    let lng_values = lng_ca
        .cont_slice()
        .expect("No nulls expected in lng_series");

    let cells: Vec<Option<CellIndex>> = lat_values
        .par_iter()
        .zip(lng_values.par_iter())
        .map(|(&lat, &lng)| match LatLng::new(lat, lng) {
            Ok(coord) => Some(coord.to_cell(res)),
            Err(_) => None,
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
