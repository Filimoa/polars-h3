use h3o::CellIndex;
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

pub fn grid_ring(cell_series: &Series, k: u32) -> PolarsResult<Series> {
    let original_dtype = cell_series.dtype().clone();
    let cells = parse_cell_indices(cell_series)?;

    let rings: ListChunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.map(|idx| {
                let ring_cells: Vec<u64> = idx
                    .grid_ring_fast(k)
                    .filter_map(|opt_cell| opt_cell.map(Into::into))
                    .collect();
                Series::new(PlSmallStr::from(""), ring_cells.as_slice())
            })
        })
        .collect();

    let rings_series = rings.into_series();
    let target_inner_dtype = resolve_target_inner_dtype(&original_dtype)?;
    cast_list_u64_to_dtype(&rings_series, &DataType::UInt64, Some(&target_inner_dtype))
}

pub fn grid_disk(cell_series: &Series, k: u32) -> PolarsResult<Series> {
    let original_dtype = cell_series.dtype().clone();
    let cells = parse_cell_indices(cell_series)?;
    let disks: ListChunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.map(|idx| {
                let disk_cells: Vec<_> = CellIndex::grid_disks_fast(vec![idx], k)
                    .flatten() // Flatten the Option<CellIndex>
                    .map(Into::<u64>::into) // Convert CellIndex to u64
                    .collect();
                Series::new(PlSmallStr::from(""), disk_cells.as_slice())
            })
        })
        .collect();
    let disks_series = disks.into_series();
    let target_inner_dtype = resolve_target_inner_dtype(&original_dtype)?;
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
        .map(|(cell, origin)| {
            match (cell, origin) {
                (Some(cell), Some(origin)) => {
                    cell.to_local_ij(origin).ok().map(|local_ij| {
                        // Convert to [i, j] coordinates
                        Series::new(
                            PlSmallStr::from(""),
                            &[local_ij.i() as f64, local_ij.j() as f64],
                        )
                    })
                },
                _ => None,
            }
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

    // Convert inputs to i32, handling errors appropriately
    let i_coords = i_series.cast(&DataType::Int32)?;
    let j_coords = j_series.cast(&DataType::Int32)?;

    let i_values = i_coords.i32()?;
    let j_values = j_coords.i32()?;

    let cells: UInt64Chunked = origins
        .into_iter()
        .zip(i_values.into_iter().zip(j_values))
        .map(|(origin, (i, j))| match (origin, i, j) {
            (Some(origin), Some(i), Some(j)) => {
                // Create LocalIJ directly from coordinates
                let local_ij = h3o::LocalIJ::new_unchecked(origin, i, j);
                // Convert to cell index
                CellIndex::try_from(local_ij).ok().map(Into::into)
            },
            _ => None,
        })
        .collect();

    Ok(cells.into_series())
}
