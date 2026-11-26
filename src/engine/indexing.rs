use h3o::{CellIndex, LatLng, Resolution};
use polars::prelude::*;
use rayon::prelude::*;

use super::utils::{map_cells, parallel_chunks, parse_cell_indices};

fn map_latlng<T, R, F>(
    lat_series: &Series,
    lng_series: &Series,
    resolution: u8,
    op: F,
) -> PolarsResult<Series>
where
    T: PolarsDataType,
    ChunkedArray<T>: FromIterator<Option<R>> + IntoSeries,
    F: Fn(CellIndex) -> R + Sync + Send,
{
    let lat_vals = match lat_series.dtype() {
        DataType::Float64 => lat_series.clone(),
        DataType::Float32 => lat_series.cast(&DataType::Float64)?,
        _ => {
            return Err(PolarsError::ComputeError(
                "lat column must be Float32 or Float64".into(),
            ))
        },
    };

    let lng_vals = match lng_series.dtype() {
        DataType::Float64 => lng_series.clone(),
        DataType::Float32 => lng_series.cast(&DataType::Float64)?,
        _ => {
            return Err(PolarsError::ComputeError(
                "lng column must be Float32 or Float64".into(),
            ))
        },
    };

    let resolution = Resolution::try_from(resolution)
        .map_err(|_| polars_err!(ComputeError: "Invalid resolution: {}", resolution))?;

    parallel_chunks(lat_vals.len().min(lng_vals.len()), |offset, len| {
        let lat = lat_vals.slice(offset as i64, len);
        let lng = lng_vals.slice(offset as i64, len);
        let cells: ChunkedArray<T> = lat
            .f64()?
            .iter()
            .zip(lng.f64()?.iter())
            .map(|(lat, lng)| {
                let coord = LatLng::new(lat?, lng?).ok()?;
                Some(op(coord.to_cell(resolution)))
            })
            .collect();
        Ok(cells.into_series())
    })
}

pub fn latlng_to_cell(
    lat_series: &Series,
    lng_series: &Series,
    resolution: u8,
) -> PolarsResult<Series> {
    map_latlng::<UInt64Type, _, _>(lat_series, lng_series, resolution, u64::from)
}

pub fn latlng_to_cell_string(
    lat_series: &Series,
    lng_series: &Series,
    resolution: u8,
) -> PolarsResult<Series> {
    map_latlng::<StringType, _, _>(lat_series, lng_series, resolution, |cell| cell.to_string())
}

pub fn cell_to_lat(cell_series: &Series) -> PolarsResult<Series> {
    map_cells::<Float64Type, _, _>(cell_series, |cell| cell.map(|idx| LatLng::from(idx).lat()))
}

pub fn cell_to_lng(cell_series: &Series) -> PolarsResult<Series> {
    map_cells::<Float64Type, _, _>(cell_series, |cell| cell.map(|idx| LatLng::from(idx).lng()))
}

pub fn cell_to_latlng(cell_series: &Series) -> PolarsResult<Series> {
    parallel_chunks(cell_series.len(), |offset, len| {
        let cells = parse_cell_indices(&cell_series.slice(offset as i64, len))?;
        let mut builder = ListPrimitiveChunkedBuilder::<Float64Type>::new(
            PlSmallStr::from(""),
            len,
            len * 2,
            DataType::Float64,
        );
        for cell in cells {
            match cell {
                Some(cell) => {
                    let coord = LatLng::from(cell);
                    builder.append_slice(&[coord.lat(), coord.lng()]);
                },
                None => builder.append_null(),
            }
        }
        Ok(builder.finish().into_series())
    })
}

pub fn cell_to_boundary(cell_series: &Series) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let coords: ListChunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.map(|idx| {
                let boundary = idx.boundary();
                let mut builder = ListPrimitiveChunkedBuilder::<Float64Type>::new(
                    PlSmallStr::from(""),
                    boundary.len(),
                    boundary.len() * 2,
                    DataType::Float64,
                );

                for vertex in boundary.iter() {
                    builder.append_slice(&[vertex.lat(), vertex.lng()]);
                }

                builder.finish().into_series()
            })
        })
        .collect();

    Ok(coords.into_series())
}
