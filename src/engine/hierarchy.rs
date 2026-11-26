use h3o::{CellIndex, Resolution};
use polars::prelude::*;
use rayon::prelude::*;

use super::utils::{
    cast_list_u64_to_dtype, cast_u64_to_dtype, list_u64_vecs_to_series, map_cell_lists, map_cells,
    parse_cell_indices, resolve_target_inner_dtype,
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
    let parents = map_cells::<UInt64Type, _, _>(cell_series, |cell| {
        cell.and_then(|idx| {
            let target_res = match parent_res {
                Some(res) => Resolution::try_from(res).ok(),
                None => idx.resolution().pred(),
            };
            target_res.and_then(|res| idx.parent(res))
        })
        .map(Into::into)
    })?;

    cast_u64_to_dtype(&original_dtype, None, parents.u64()?.clone())
}

pub fn cell_to_center_child(cell_series: &Series, child_res: Option<u8>) -> PolarsResult<Series> {
    let original_dtype = cell_series.dtype().clone();
    let center_children = map_cells::<UInt64Type, _, _>(cell_series, |cell| {
        cell.and_then(|idx| {
            let target_res = get_target_resolution(idx, child_res)?;
            idx.center_child(target_res)
        })
        .map(Into::into)
    })?;

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
    cast_u64_to_dtype(
        &original_dtype,
        Some(&target_dtype),
        center_children.u64()?.clone(),
    )
}

pub fn cell_to_children_size(cell_series: &Series, child_res: Option<u8>) -> PolarsResult<Series> {
    map_cells::<UInt64Type, _, _>(cell_series, |cell| {
        cell.map(|idx| {
            let target_res = get_target_resolution(idx, child_res)
                .unwrap_or_else(|| idx.resolution().succ().unwrap_or(idx.resolution()));
            idx.children_count(target_res)
        })
    })
}

pub fn cell_to_children(cell_series: &Series, child_res: Option<u8>) -> PolarsResult<Series> {
    let original_dtype = cell_series.dtype().clone();
    let children = map_cell_lists(cell_series, 7, |idx, builder| {
        let target_res = get_target_resolution(idx, child_res)
            .unwrap_or_else(|| idx.resolution().succ().unwrap_or(idx.resolution()));
        builder.append_values_iter(idx.children(target_res).map(u64::from));
    })?;

    let target_dtype = resolve_target_inner_dtype(&original_dtype)?;
    match target_dtype {
        DataType::UInt64 => Ok(children),
        DataType::Int64 => children.cast(&DataType::List(Box::new(DataType::Int64))),
        _ => cast_list_u64_to_dtype(&children, &DataType::UInt64, Some(&target_dtype)),
    }
}

pub fn cell_to_child_pos(child_series: &Series, parent_res: u8) -> PolarsResult<Series> {
    map_cells::<UInt64Type, _, _>(child_series, |cell| {
        cell.and_then(|idx| {
            let parent_res = Resolution::try_from(parent_res).ok()?;
            idx.child_position(parent_res)
        })
    })
}

pub fn child_pos_to_cell(
    parent_series: &Series,
    child_res: u8,
    pos_series: &Series,
) -> PolarsResult<Series> {
    let original_dtype = parent_series.dtype().clone();
    let parents = parse_cell_indices(parent_series)?;
    let positions = pos_series.u64()?;

    let pos_vec: Vec<Option<u64>> = positions.iter().collect();

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
    let compacted_values: Vec<Option<Vec<u64>>> = if let DataType::List(_) = cell_series.dtype() {
        // Input is already a List column
        let ca = cell_series.list()?;
        let cells_vec: Vec<_> = ca.series_iter().collect();

        cells_vec
            .into_par_iter()
            .map(|opt_series| {
                opt_series
                    .map(|series| {
                        let cells = parse_cell_indices(&series)?;
                        let mut cell_vec: Vec<_> = cells.into_iter().flatten().collect();

                        CellIndex::compact(&mut cell_vec).map_err(|e| {
                            PolarsError::ComputeError(format!("Compaction error: {}", e).into())
                        })?;
                        Ok(cell_vec.into_iter().map(u64::from).collect())
                    })
                    .transpose()
            })
            .collect::<PolarsResult<_>>()?
    } else {
        // Input is not a list, so we treat it as a single column of cells.
        let cells = parse_cell_indices(cell_series)?;
        let mut cell_vec: Vec<_> = cells.into_iter().flatten().collect();

        CellIndex::compact(&mut cell_vec)
            .map_err(|e| PolarsError::ComputeError(format!("Compaction error: {}", e).into()))?;

        vec![Some(cell_vec.into_iter().map(u64::from).collect())]
    };

    // Determine the target inner dtype based on the original column
    // If the original was a List, extract its inner type. Otherwise, use the original directly.
    let inner_original_dtype = match &original_dtype {
        DataType::List(inner) => *inner.clone(),
        dt => dt.clone(),
    };

    let target_inner_dtype = resolve_target_inner_dtype(&inner_original_dtype)?;

    list_u64_vecs_to_series(PlSmallStr::from(""), compacted_values, &target_inner_dtype)
}

pub fn uncompact_cells(cell_series: &Series, res: u8) -> PolarsResult<Series> {
    let original_dtype = cell_series.dtype().clone();
    let target_res = Resolution::try_from(res)
        .map_err(|_| PolarsError::ComputeError("Invalid resolution".into()))?;

    // Perform the uncompact logic
    let uncompacted_values: Vec<Option<Vec<u64>>> = if let DataType::List(_) = cell_series.dtype() {
        // Input is already a List column
        let ca = cell_series.list()?;
        let cells_vec: Vec<_> = ca.series_iter().collect();

        cells_vec
            .into_par_iter()
            .map(|opt_series| {
                opt_series
                    .map(|series| {
                        let cells = parse_cell_indices(&series)?;
                        let cell_vec: Vec<_> = cells.into_iter().flatten().collect();

                        let uncompacted = CellIndex::uncompact(cell_vec, target_res);
                        Ok(uncompacted.into_iter().map(u64::from).collect())
                    })
                    .transpose()
            })
            .collect::<PolarsResult<_>>()?
    } else {
        // Input is not a list, treat it as a single column of cells.
        let cells = parse_cell_indices(cell_series)?;
        let cell_vec: Vec<_> = cells.into_iter().flatten().collect();

        let uncompacted = CellIndex::uncompact(cell_vec, target_res);
        vec![Some(uncompacted.into_iter().map(u64::from).collect())]
    };

    // Determine the target inner dtype based on the original column
    let inner_original_dtype = match &original_dtype {
        DataType::List(inner) => *inner.clone(),
        dt => dt.clone(),
    };

    // Map original inner dtype to the target dtype
    let target_inner_dtype = resolve_target_inner_dtype(&inner_original_dtype)?;
    list_u64_vecs_to_series(
        PlSmallStr::from(""),
        uncompacted_values,
        &target_inner_dtype,
    )
}
