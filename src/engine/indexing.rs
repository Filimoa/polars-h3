use h3o::{CellIndex, LatLng, Resolution};
use polars::prelude::*;
use rayon::prelude::*;

use super::utils::{apply_batches, map_cell_indices, parse_cell_indices, HexStringBuilder};

fn map_latlng<F>(
    lat_series: &Series,
    lng_series: &Series,
    resolution: u8,
    op: F,
) -> PolarsResult<Series>
where
    F: Fn(&Float64Chunked, &Float64Chunked, Resolution) -> Series + Sync,
{
    let lat_vals = match lat_series.dtype() {
        DataType::Float64 | DataType::Float32 => lat_series.cast(&DataType::Float64)?,
        _ => {
            return Err(PolarsError::ComputeError(
                "lat column must be Float32 or Float64".into(),
            ))
        },
    };

    let lng_vals = match lng_series.dtype() {
        DataType::Float64 | DataType::Float32 => lng_series.cast(&DataType::Float64)?,
        _ => {
            return Err(PolarsError::ComputeError(
                "lng column must be Float32 or Float64".into(),
            ))
        },
    };

    let resolution = Resolution::try_from(resolution)
        .map_err(|_| polars_err!(ComputeError: "Invalid resolution: {}", resolution))?;

    let lat_vals = lat_vals.f64()?;
    let lng_vals = lng_vals.f64()?;
    apply_batches(lat_vals.len().min(lng_vals.len()), |offset, len| {
        let lat = lat_vals.slice(offset as i64, len);
        let lng = lng_vals.slice(offset as i64, len);
        Ok(op(&lat, &lng, resolution))
    })
}

fn cells_from_latlng<'a>(
    lat: &'a Float64Chunked,
    lng: &'a Float64Chunked,
    resolution: Resolution,
) -> impl Iterator<Item = Option<CellIndex>> + 'a {
    lat.iter().zip(lng.iter()).map(move |(lat, lng)| {
        LatLng::new(lat?, lng?)
            .ok()
            .map(|coord| coord.to_cell(resolution))
    })
}

pub fn latlng_to_cell(
    lat_series: &Series,
    lng_series: &Series,
    resolution: u8,
) -> PolarsResult<Series> {
    map_latlng(lat_series, lng_series, resolution, |lat, lng, res| {
        let indices: UInt64Chunked = cells_from_latlng(lat, lng, res)
            .map(|cell| cell.map(Into::into))
            .collect();
        indices.into_series()
    })
}

pub fn latlng_to_cell_string(
    lat_series: &Series,
    lng_series: &Series,
    resolution: u8,
) -> PolarsResult<Series> {
    map_latlng(lat_series, lng_series, resolution, |lat, lng, res| {
        let mut builder = HexStringBuilder::new(lat.len());
        for cell in cells_from_latlng(lat, lng, res) {
            builder.append(cell.map(Into::into));
        }
        builder.finish().into_series()
    })
}

pub fn cell_to_lat(cell_series: &Series) -> PolarsResult<Series> {
    apply_batches(cell_series.len(), |offset, len| {
        let cells = cell_series.slice(offset as i64, len);
        let lats: Float64Chunked =
            map_cell_indices(&cells, |cell| cell.map(|idx| LatLng::from(idx).lat()))?;
        Ok(lats.into_series())
    })
}

pub fn cell_to_lng(cell_series: &Series) -> PolarsResult<Series> {
    apply_batches(cell_series.len(), |offset, len| {
        let cells = cell_series.slice(offset as i64, len);
        let lngs: Float64Chunked =
            map_cell_indices(&cells, |cell| cell.map(|idx| LatLng::from(idx).lng()))?;
        Ok(lngs.into_series())
    })
}

pub fn cell_to_latlng(cell_series: &Series) -> PolarsResult<Series> {
    apply_batches(cell_series.len(), |offset, len| {
        let cells = cell_series.slice(offset as i64, len);
        let mut builder = ListPrimitiveChunkedBuilder::<Float64Type>::new(
            PlSmallStr::EMPTY,
            len,
            len * 2,
            DataType::Float64,
        );
        map_cell_indices::<(), _, _>(&cells, |cell| match cell {
            Some(idx) => {
                let latlng = LatLng::from(idx);
                builder.append_slice(&[latlng.lat(), latlng.lng()]);
            },
            None => builder.append_null(),
        })?;
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
