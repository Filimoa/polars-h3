use h3o::{CellIndex, Resolution};
use polars::prelude::*;
use rayon::prelude::*;

use super::utils::{
    cast_list_u64_to_dtype, cast_u64_to_dtype, parse_cell_indices, resolve_target_inner_dtype,
};

fn get_target_resolution(cell: CellIndex, target_res: Option<u8>) -> Option<Resolution> {
    match target_res {
        Some(res) => Resolution::try_from(res).ok(),
        None => {
            let curr_res = cell.resolution();
            // Get next resolution if None provided
            curr_res.succ()
        },
    }
}

pub fn cell_to_parent(cell_series: &Series, parent_res: Option<u8>) -> PolarsResult<Series> {
    let original_dtype = cell_series.dtype().clone();
    let cells = parse_cell_indices(cell_series)?;

    let parents: UInt64Chunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.and_then(|idx| {
                let target_res = match parent_res {
                    Some(res) => Resolution::try_from(res).ok(),
                    None => idx.resolution().pred(),
                };
                target_res.and_then(|res| idx.parent(res))
            })
            .map(Into::into)
        })
        .collect();

    cast_u64_to_dtype(&original_dtype, None, parents)
}

pub fn cell_to_center_child(cell_series: &Series, child_res: Option<u8>) -> PolarsResult<Series> {
    let original_dtype = cell_series.dtype().clone();
    let cells = parse_cell_indices(cell_series)?;

    let center_children: UInt64Chunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.and_then(|idx| {
                let target_res = get_target_resolution(idx, child_res)?;
                idx.center_child(target_res)
            })
            .map(Into::into)
        })
        .collect();

    let target_dtype = match original_dtype {
        DataType::UInt64 => DataType::UInt64,
        DataType::Int64 => DataType::Int64,
        DataType::String => DataType::String,
        _ => {
            return Err(PolarsError::ComputeError(
                format!(
                    "Unsupported original dtype for cell_to_center_child: {:?}",
                    original_dtype
                )
                .into(),
            ))
        },
    };

    // Cast the UInt64Chunked result to the correct dtype
    cast_u64_to_dtype(&original_dtype, Some(&target_dtype), center_children)
}

pub fn cell_to_children_size(cell_series: &Series, child_res: Option<u8>) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let sizes: UInt64Chunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.map(|idx| {
                let target_res = get_target_resolution(idx, child_res)
                    .unwrap_or_else(|| idx.resolution().succ().unwrap_or(idx.resolution()));
                idx.children_count(target_res)
            })
        })
        .collect();

    Ok(sizes.into_series())
}

pub fn cell_to_children(cell_series: &Series, child_res: Option<u8>) -> PolarsResult<Series> {
    let original_dtype = cell_series.dtype().clone();
    let cells = parse_cell_indices(cell_series)?;

    let children: ListChunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.map(|idx| {
                let target_res = get_target_resolution(idx, child_res)
                    .unwrap_or_else(|| idx.resolution().succ().unwrap_or(idx.resolution()));
                let children: Vec<u64> = idx.children(target_res).map(Into::into).collect();
                Series::new(PlSmallStr::from(""), children.as_slice())
            })
        })
        .collect();

    let children_series = children.into_series();

    let target_dtype = resolve_target_inner_dtype(&original_dtype)?;
    let casted_children =
        cast_list_u64_to_dtype(&children_series, &DataType::UInt64, Some(&target_dtype))?;
    Ok(casted_children)
}

pub fn cell_to_child_pos(child_series: &Series, parent_res: u8) -> PolarsResult<Series> {
    let cells = parse_cell_indices(child_series)?;

    let positions: UInt64Chunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.and_then(|idx| {
                let parent_res = Resolution::try_from(parent_res).ok()?;
                idx.child_position(parent_res)
            })
        })
        .collect();

    Ok(positions.into_series())
}

pub fn child_pos_to_cell(
    parent_series: &Series,
    child_res: u8,
    pos_series: &Series,
) -> PolarsResult<Series> {
    let original_dtype = parent_series.dtype().clone();
    let parents = parse_cell_indices(parent_series)?;
    let positions = pos_series.u64()?;

    let pos_vec: Vec<Option<u64>> = positions.into_iter().collect();

    let children: UInt64Chunked = parents
        .into_par_iter()
        .zip(pos_vec.into_par_iter())
        .map(|(parent, pos)| match (parent, pos) {
            (Some(parent), Some(pos)) => {
                let child_res = Resolution::try_from(child_res).ok()?;
                parent.child_at(pos, child_res).map(Into::into)
            },
            _ => None,
        })
        .collect();

    let target_dtype = resolve_target_inner_dtype(&original_dtype)?;

    cast_u64_to_dtype(&original_dtype, Some(&target_dtype), children)
}

pub fn compact_cells(cell_series: &Series) -> PolarsResult<Series> {
    let original_dtype = cell_series.dtype().clone();

    // Perform the compaction logic
    let out_series = if let DataType::List(_) = cell_series.dtype() {
        // Input is already a List column
        let ca = cell_series.list()?;
        let cells_vec: Vec<_> = ca.into_iter().collect();

        let compacted: ListChunked = cells_vec
            .into_par_iter()
            .map(|opt_series| {
                opt_series
                    .map(|series| {
                        let cells = parse_cell_indices(&series)?;
                        let cell_vec: Vec<_> = cells.into_iter().flatten().collect();

                        CellIndex::compact(cell_vec)
                            .map_err(|e| {
                                PolarsError::ComputeError(format!("Compaction error: {}", e).into())
                            })
                            .map(|compacted| {
                                // Note: `compacted` is a Vec<CellIndex>.
                                // Convert to `u64` and store as a Series of UInt64.
                                let compacted_u64: Vec<u64> =
                                    compacted.into_iter().map(u64::from).collect();
                                Series::new(PlSmallStr::from(""), compacted_u64.as_slice())
                            })
                    })
                    .transpose()
            })
            .collect::<PolarsResult<_>>()?;

        compacted.into_series()
    } else {
        // Input is not a list, so we treat it as a single column of cells.
        let cells = parse_cell_indices(cell_series)?;
        let cell_vec: Vec<_> = cells.into_iter().flatten().collect();

        let compacted = CellIndex::compact(cell_vec)
            .map_err(|e| PolarsError::ComputeError(format!("Compaction error: {}", e).into()))?;

        // Wrap in a single List
        let compacted_u64: Vec<u64> = compacted.into_iter().map(u64::from).collect();
        let compacted_cells: ListChunked = vec![Some(Series::new(
            PlSmallStr::from(""),
            compacted_u64.as_slice(),
        ))]
        .into_iter()
        .collect();

        compacted_cells.into_series()
    };

    // Determine the target inner dtype based on the original column
    // If the original was a List, extract its inner type. Otherwise, use the original directly.
    let inner_original_dtype = match &original_dtype {
        DataType::List(inner) => *inner.clone(),
        dt => dt.clone(),
    };

    let target_inner_dtype = resolve_target_inner_dtype(&inner_original_dtype)?;

    cast_list_u64_to_dtype(&out_series, &DataType::UInt64, Some(&target_inner_dtype))
}

pub fn uncompact_cells(cell_series: &Series, res: u8) -> PolarsResult<Series> {
    let original_dtype = cell_series.dtype().clone();
    let target_res = Resolution::try_from(res)
        .map_err(|_| PolarsError::ComputeError("Invalid resolution".into()))?;

    // Perform the uncompact logic
    let out_series = if let DataType::List(_) = cell_series.dtype() {
        // Input is already a List column
        let ca = cell_series.list()?;
        let cells_vec: Vec<_> = ca.into_iter().collect();

        let uncompacted: ListChunked = cells_vec
            .into_par_iter()
            .map(|opt_series| {
                opt_series
                    .map(|series| {
                        let cells = parse_cell_indices(&series)?;
                        let cell_vec: Vec<_> = cells.into_iter().flatten().collect();

                        let uncompacted = CellIndex::uncompact(cell_vec, target_res);
                        // Convert the CellIndex result to a UInt64 Series
                        let uncompacted_u64: Vec<u64> =
                            uncompacted.into_iter().map(u64::from).collect();
                        Ok(Series::new(
                            PlSmallStr::from(""),
                            uncompacted_u64.as_slice(),
                        ))
                    })
                    .transpose()
            })
            .collect::<PolarsResult<_>>()?;

        uncompacted.into_series()
    } else {
        // Input is not a list, treat it as a single column of cells.
        let cells = parse_cell_indices(cell_series)?;
        let cell_vec: Vec<_> = cells.into_iter().flatten().collect();

        let uncompacted = CellIndex::uncompact(cell_vec, target_res);
        let uncompacted_u64: Vec<u64> = uncompacted.into_iter().map(u64::from).collect();

        // Wrap in a single List
        let uncompacted_cells: ListChunked = vec![Some(Series::new(
            PlSmallStr::from(""),
            uncompacted_u64.as_slice(),
        ))]
        .into_iter()
        .collect();

        uncompacted_cells.into_series()
    };

    // Determine the target inner dtype based on the original column
    let inner_original_dtype = match &original_dtype {
        DataType::List(inner) => *inner.clone(),
        dt => dt.clone(),
    };

    // Map original inner dtype to the target dtype
    let target_inner_dtype = resolve_target_inner_dtype(&inner_original_dtype)?;
    // We have a List(UInt64) right now, cast it to List(target_inner_dtype)
    cast_list_u64_to_dtype(&out_series, &DataType::UInt64, Some(&target_inner_dtype))
}
