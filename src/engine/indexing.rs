use h3o::{CellIndex, LatLng, Resolution};
use polars::prelude::*;

use super::utils::{
    for_each_index, map_cells, map_index_lists, parallel_chunks, parallel_chunks_with_min,
};

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
    map_index_lists::<CellIndex, Float64Type, _>(
        cell_series,
        "h3 cell",
        2,
        16_384,
        |idx, builder| {
            let coord = LatLng::from(idx);
            builder.append_slice(&[coord.lat(), coord.lng()]);
        },
    )
}

pub fn cell_to_boundary(cell_series: &Series) -> PolarsResult<Series> {
    let output = parallel_chunks_with_min(cell_series.len(), 1024, |offset, len| {
        // One coordinate builder per batch, with an outer offset for each cell.
        // Retain List(List(Float64)), including null outer rows and vertex order.
        let mut coords = ListPrimitiveChunkedBuilder::<Float64Type>::new(
            PlSmallStr::EMPTY,
            len * 6,
            len * 12,
            DataType::Float64,
        );
        let mut offsets = Vec::<i64>::with_capacity(len + 1);
        let mut validity = Vec::with_capacity(len);
        let mut vertices = 0i64;
        offsets.push(vertices);
        for_each_index::<CellIndex, _>(
            &cell_series.slice(offset as i64, len),
            "h3 cell",
            |cell| {
                validity.push(cell.is_some());
                if let Some(cell) = cell {
                    let boundary = cell.boundary();
                    for coord in boundary.iter() {
                        coords.append_slice(&[coord.lat(), coord.lng()]);
                    }
                    vertices += boundary.len() as i64;
                }
                offsets.push(vertices);
            },
        )?;
        let values = coords.finish().into_series();
        let array = LargeListArray::new(
            LargeListArray::default_datatype(values.chunks()[0].dtype().clone()),
            offsets.try_into().expect("monotonic boundary offsets"),
            values.chunks()[0].clone(),
            Some(validity.into_iter().collect()),
        );
        Ok(ListChunked::with_chunk(PlSmallStr::EMPTY, array).into_series())
    })?;
    // Keep the old collector's dtype for empty or entirely invalid inputs.
    if output.null_count() == output.len() {
        Ok(Series::full_null(
            PlSmallStr::EMPTY,
            output.len(),
            &DataType::List(Box::new(DataType::Null)),
        ))
    } else {
        Ok(output)
    }
}
