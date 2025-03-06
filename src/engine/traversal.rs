use h3o::CellIndex;
use h3o::CoordIJ;
use polars::prelude::*;
use rayon::prelude::*;

use super::utils::{cast_list_u64_to_dtype, parse_cell_indices, resolve_target_inner_dtype};

pub fn grid_distance(origin_series: &Series, destination_series: &Series) -> PolarsResult<Series> {
    let origins = parse_cell_indices(origin_series)?;
    let destinations = parse_cell_indices(destination_series)?;

    // Convert to Vec to ensure parallel iteration works
    let dest_vec: Vec<_> = destinations.into_iter().collect();

    let distances: Int32Chunked = origins
        .into_par_iter()
        .zip(dest_vec.into_par_iter())
        .map(|(origin, dest)| match (origin, dest) {
            (Some(org), Some(dst)) => org.grid_distance(dst).ok(),
            _ => None,
        })
        .collect();

    Ok(distances.into_series())
}

pub fn grid_ring(inputs: &[Series]) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    let k_series = &inputs[1];

    let cells = super::utils::parse_cell_indices(cell_series)?;
    let k_cast = k_series.cast(&DataType::Int32)?;
    let k_i32 = k_cast.i32()?;

    let cells_vec: Vec<_> = cells.into_iter().collect();
    let is_scalar_k = k_series.len() == 1 && !matches!(k_series.dtype(), DataType::List(_));
    let ring_results: Vec<Option<Vec<u64>>> = if is_scalar_k {
        // Scalar case: broadcast the single k value across all cells
        let k_val = k_i32
            .get(0)
            .ok_or_else(|| polars_err!(ComputeError: "k_series is empty or invalid"))?;
        if k_val < 0 {
            return Err(polars_err!(ComputeError: "k must be non-negative"));
        }
        cells_vec
            .into_par_iter()
            .map(|maybe_cell| match maybe_cell {
                Some(cell) => {
                    let k_u32 = k_val as u32;
                    Some(
                        cell.grid_ring_fast(k_u32)
                            .flatten()
                            .map(Into::into)
                            .collect(),
                    )
                },
                _ => None,
            })
            .collect()
    } else {
        // Column case: zip with k values
        let k_vec: Vec<_> = k_i32.into_iter().collect();
        if k_vec.len() != cells_vec.len() {
            return Err(polars_err!(
                ComputeError: "Length of k_series ({}) must match cell_series ({})",
                k_vec.len(),
                cells_vec.len()
            ));
        }
        cells_vec
            .into_par_iter()
            .zip(k_vec.into_par_iter())
            .map(|(maybe_cell, maybe_k)| match (maybe_cell, maybe_k) {
                (Some(cell), Some(k_val)) if k_val >= 0 => {
                    let k_u32 = k_val as u32;
                    Some(
                        cell.grid_ring_fast(k_u32)
                            .flatten()
                            .map(Into::into)
                            .collect(),
                    )
                },
                _ => None,
            })
            .collect()
    };

    let rings: ListChunked = ring_results
        .into_iter()
        .map(|opt| opt.map(|rings| Series::new(PlSmallStr::from(""), rings.as_slice())))
        .collect::<Vec<_>>()
        .into_iter()
        .collect();

    let target_inner_dtype = super::utils::resolve_target_inner_dtype(cell_series.dtype())?;
    super::utils::cast_list_u64_to_dtype(
        &rings.into_series(),
        &DataType::UInt64,
        Some(&target_inner_dtype),
    )
}

pub fn grid_disk(inputs: &[Series]) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    let k_series = &inputs[1];

    let original_dtype = cell_series.dtype().clone();
    let cells = parse_cell_indices(cell_series)?;
    let target_inner_dtype = resolve_target_inner_dtype(&original_dtype)?;

    // Cast k_series to Int32 to handle various integer inputs
    let k_cast = k_series.cast(&DataType::Int32)?;
    let k_i32 = k_cast.i32()?;

    let cells_vec: Vec<_> = cells.into_iter().collect();

    let is_scalar_k = k_series.len() == 1 && !matches!(k_series.dtype(), DataType::List(_));

    let disk_results: Vec<Option<Vec<u64>>> = if is_scalar_k {
        // Scalar case: broadcast the single k value
        let k_val = k_i32
            .get(0)
            .ok_or_else(|| polars_err!(ComputeError: "k_series is empty"))?;
        if k_val >= 0 {
            let k_u32 = k_val as u32;
            cells_vec
                .into_par_iter()
                .map(|maybe_cell| {
                    maybe_cell.map(|cell| {
                        cell.grid_disk::<Vec<_>>(k_u32)
                            .into_iter()
                            .map(Into::into)
                            .collect()
                    })
                })
                .collect()
        } else {
            // If k < 0, return None for all rows
            vec![None; cells_vec.len()]
        }
    } else {
        // Non-scalar case: k_series should match cell_series length
        let k_vec: Vec<_> = k_i32.into_iter().collect();
        if k_vec.len() != cells_vec.len() {
            return Err(polars_err!(
                ComputeError: "k_series length ({}) must match cell_series length ({})",
                k_vec.len(),
                cells_vec.len()
            ));
        }
        cells_vec
            .into_par_iter()
            .zip(k_vec.into_par_iter())
            .map(|(maybe_cell, maybe_k)| match (maybe_cell, maybe_k) {
                (Some(cell), Some(k_val)) if k_val >= 0 => {
                    let k_u32 = k_val as u32;
                    Some(
                        cell.grid_disk::<Vec<_>>(k_u32)
                            .into_iter()
                            .map(Into::into)
                            .collect(),
                    )
                },
                _ => None,
            })
            .collect()
    };

    // Convert results to a ListChunked series
    let disks: ListChunked = disk_results
        .into_iter()
        .map(|opt| opt.map(|disk| Series::new(PlSmallStr::from(""), disk.as_slice())))
        .collect();

    let disks_series = disks.into_series();
    cast_list_u64_to_dtype(&disks_series, &DataType::UInt64, Some(&target_inner_dtype))
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

    let paths: ListChunked = origins
        .into_par_iter()
        .zip(dest_vec.into_par_iter())
        .map(|(origin, dest)| {
            match (origin, dest) {
                (Some(org), Some(dst)) => {
                    // Collect all cells in the path, handling errors by returning None
                    org.grid_path_cells(dst).ok().map(|path| {
                        let path_cells: Vec<u64> =
                            path.filter_map(Result::ok).map(Into::into).collect();
                        Series::new(PlSmallStr::from(""), path_cells.as_slice())
                    })
                },
                _ => None,
            }
        })
        .collect();

    let paths_series = paths.into_series();
    let target_inner_dtype = resolve_target_inner_dtype(&original_dtype)?;
    cast_list_u64_to_dtype(&paths_series, &DataType::UInt64, Some(&target_inner_dtype))
}

pub fn cell_to_local_ij(cell_series: &Series, origin_series: &Series) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;
    let origins = parse_cell_indices(origin_series)?;

    let origin_vec: Vec<_> = origins.into_iter().collect();

    let coords: ListChunked = cells
        .into_par_iter()
        .zip(origin_vec.into_par_iter())
        .map(|(cell, origin)| match (cell, origin) {
            (Some(cell), Some(origin)) => cell.to_local_ij(origin).ok().map(|local_ij| {
                Series::new(
                    PlSmallStr::from(""),
                    &[local_ij.coord.i as f64, local_ij.coord.j as f64],
                )
            }),
            _ => None,
        })
        .collect();

    Ok(coords.into_series())
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

    let cells: UInt64Chunked = origins
        .into_iter()
        .zip(i_values.into_iter().zip(j_values))
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
