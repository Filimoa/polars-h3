use h3o::{CellIndex, CoordIJ};
use polars::prelude::*;
use rayon::prelude::*;

use super::utils::{
    cast_list_u64_to_dtype, list_u64_vecs_to_series, map_cell_pairs, parallel_chunks,
    parse_cell_indices, resolve_target_inner_dtype,
};

pub fn grid_distance(origin_series: &Series, destination_series: &Series) -> PolarsResult<Series> {
    map_cell_pairs::<Int32Type, _, _>(origin_series, destination_series, |origin, dest| {
        match (origin, dest) {
            (Some(org), Some(dst)) => org.grid_distance(dst).ok(),
            _ => None,
        }
    })
}

pub fn grid_ring(inputs: &[Series]) -> PolarsResult<Series> {
    grid_lists(inputs, false)
}

pub fn grid_disk(inputs: &[Series]) -> PolarsResult<Series> {
    grid_lists(inputs, true)
}

fn grid_lists(inputs: &[Series], disk: bool) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    let k_series = &inputs[1];
    // Check the input type before radius errors, without parsing the full column.
    parse_cell_indices(&cell_series.slice(0, 0))?;
    let target_dtype = resolve_target_inner_dtype(cell_series.dtype())?;
    let k_cast = k_series.cast(&DataType::Int32)?;
    let radii = k_cast.i32()?;
    let scalar = k_series.len() == 1 && !matches!(k_series.dtype(), DataType::List(_));
    let scalar_k = if scalar {
        let k = radii.get(0).ok_or_else(|| {
            PolarsError::ComputeError(
                (if disk {
                    "k_series is empty"
                } else {
                    "k_series is empty or invalid"
                })
                .into(),
            )
        })?;
        if !disk && k < 0 {
            polars_bail!(ComputeError: "k must be non-negative");
        }
        Some(k)
    } else {
        if radii.len() != cell_series.len() {
            if disk {
                polars_bail!(ComputeError: "k_series length ({}) must match cell_series length ({})", radii.len(), cell_series.len());
            }
            polars_bail!(ComputeError: "Length of k_series ({}) must match cell_series ({})", radii.len(), cell_series.len());
        }
        None
    };

    parallel_chunks(cell_series.len(), |offset, len| {
        let cells = parse_cell_indices(&cell_series.slice(offset as i64, len))?;
        let batch_radii = radii.slice(offset as i64, if scalar { 0 } else { len });
        let mut builder = ListPrimitiveChunkedBuilder::<UInt64Type>::new(
            PlSmallStr::EMPTY,
            len,
            len * 7,
            DataType::UInt64,
        );
        // Reuse disk scratch across rows. A failed fast traversal must discard
        // its entire partial result before using the safe pentagon traversal.
        let mut scratch = Vec::new();
        for (position, cell) in cells.into_iter().enumerate() {
            let radius = scalar_k.or_else(|| batch_radii.get(position));
            match (cell, radius) {
                (Some(cell), Some(radius)) if radius >= 0 => {
                    let radius = radius as u32;
                    if disk {
                        scratch.clear();
                        let complete = cell
                            .grid_disk_fast(radius)
                            .try_for_each(|cell| cell.map(|cell| scratch.push(u64::from(cell))))
                            .is_some();
                        if !complete {
                            scratch.clear();
                            scratch.extend(cell.grid_disk_safe(radius).map(u64::from));
                        }
                        builder.append_slice(&scratch);
                    } else {
                        // Preserve the existing fast-ring API's pentagon behavior.
                        builder.append_values_iter(
                            cell.grid_ring_fast(radius).flatten().map(u64::from),
                        );
                    }
                },
                _ => builder.append_null(),
            }
        }
        let out = builder.finish().into_series();
        match &target_dtype {
            DataType::UInt64 => Ok(out),
            DataType::Int64 => out.cast(&DataType::List(Box::new(DataType::Int64))),
            _ => cast_list_u64_to_dtype(&out, &DataType::UInt64, Some(&target_dtype)),
        }
    })
}

pub fn grid_path_cells(
    origin_series: &Series,
    destination_series: &Series,
) -> PolarsResult<Series> {
    let original_dtype = origin_series.dtype().clone();
    let origins = parse_cell_indices(origin_series)?;
    let destinations = parse_cell_indices(destination_series)?;

    // Convert to Vec to ensure parallel iteration works
    let dest_vec: Vec<_> = destinations.into_iter().collect();

    let paths: Vec<Option<Vec<u64>>> = origins
        .into_par_iter()
        .zip(dest_vec.into_par_iter())
        .map(|(origin, dest)| {
            match (origin, dest) {
                (Some(org), Some(dst)) => {
                    // Collect all cells in the path, handling errors by returning None
                    org.grid_path_cells(dst)
                        .ok()
                        .map(|path| path.filter_map(Result::ok).map(Into::into).collect())
                },
                _ => None,
            }
        })
        .collect();

    let target_inner_dtype = resolve_target_inner_dtype(&original_dtype)?;
    list_u64_vecs_to_series(PlSmallStr::from(""), paths, &target_inner_dtype)
}

pub fn cell_to_local_ij(cell_series: &Series, origin_series: &Series) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;
    let origins = parse_cell_indices(origin_series)?;

    let origin_vec: Vec<_> = origins.into_iter().collect();

    let coords: Vec<Option<[f64; 2]>> = cells
        .into_par_iter()
        .zip(origin_vec.into_par_iter())
        .map(|(cell, origin)| match (cell, origin) {
            (Some(cell), Some(origin)) => cell
                .to_local_ij(origin)
                .ok()
                .map(|local_ij| [local_ij.coord.i as f64, local_ij.coord.j as f64]),
            _ => None,
        })
        .collect();

    let mut builder = ListPrimitiveChunkedBuilder::<Float64Type>::new(
        PlSmallStr::from(""),
        coords.len(),
        coords.len() * 2,
        DataType::Float64,
    );
    for opt_coord in coords {
        match opt_coord {
            Some(coord) => builder.append_slice(&coord),
            None => builder.append_null(),
        }
    }

    Ok(builder.finish().into_series())
}

pub fn local_ij_to_cell(
    origin_series: &Series,
    i_series: &Series,
    j_series: &Series,
) -> PolarsResult<Series> {
    let origins = parse_cell_indices(origin_series)?;

    let i_coords = i_series.cast(&DataType::Int32)?;
    let j_coords = j_series.cast(&DataType::Int32)?;

    let i_values = i_coords.i32()?;
    let j_values = j_coords.i32()?;
    let i_vec: Vec<_> = i_values.iter().collect();
    let j_vec: Vec<_> = j_values.iter().collect();

    let cells: UInt64Chunked = origins
        .into_par_iter()
        .zip(i_vec.into_par_iter().zip(j_vec.into_par_iter()))
        .map(|(origin, (i, j))| match (origin, i, j) {
            (Some(origin), Some(i), Some(j)) => {
                let coord = CoordIJ { i, j };
                let local_ij = h3o::LocalIJ::new(origin, coord);
                CellIndex::try_from(local_ij).ok().map(Into::into)
            },
            _ => None,
        })
        .collect();

    Ok(cells.into_series())
}
