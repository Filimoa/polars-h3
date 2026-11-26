use h3o::{CellIndex, Resolution};
use polars::prelude::*;

use super::utils::{
    cast_list_u64_to_dtype, cast_u64_to_dtype, for_each_index, map_cell_lists, map_cells,
    parallel_chunks, parallel_chunks_with_min, parse_cell_indices, resolve_target_inner_dtype,
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
    parse_cell_indices(&parent_series.slice(0, 0))?;
    let positions = pos_series.u64()?;
    let resolution = Resolution::try_from(child_res).ok();
    let children = parallel_chunks(parent_series.len().min(positions.len()), |offset, len| {
        let parents = parse_cell_indices(&parent_series.slice(offset as i64, len))?;
        let positions = positions.slice(offset as i64, len);
        let children: UInt64Chunked = parents
            .into_iter()
            .zip(positions.iter())
            .map(|(parent, pos)| parent?.child_at(pos?, resolution?).map(u64::from))
            .collect();
        Ok(children.into_series())
    })?;
    let target_dtype = resolve_target_inner_dtype(&original_dtype)?;
    cast_u64_to_dtype(
        &original_dtype,
        Some(&target_dtype),
        children.u64()?.clone(),
    )
}

fn map_cell_sets<F>(cell_series: &Series, op: F) -> PolarsResult<Series>
where
    F: Fn(&mut Vec<CellIndex>, &mut ListPrimitiveChunkedBuilder<UInt64Type>) -> PolarsResult<()>
        + Sync
        + Send,
{
    let is_list = matches!(cell_series.dtype(), DataType::List(_));
    let original_dtype = match cell_series.dtype() {
        DataType::List(inner) => inner.as_ref(),
        dtype => dtype,
    };
    let target_dtype = resolve_target_inner_dtype(original_dtype)?;
    // Input cells, rather than row count alone, approximate compaction work.
    let cells_per_row = if is_list {
        cell_series.list()?.inner_length() / cell_series.len().max(1)
    } else {
        1
    };
    let min_batch_size = (16_384 / cells_per_row.max(1)).max(1);
    let output = parallel_chunks_with_min(
        if is_list { cell_series.len() } else { 1 },
        min_batch_size,
        |offset, len| {
            let mut builder = ListPrimitiveChunkedBuilder::<UInt64Type>::new(
                PlSmallStr::EMPTY,
                len,
                len * 7,
                DataType::UInt64,
            );
            let mut cells = Vec::new();
            if is_list {
                let slice = cell_series.slice(offset as i64, len);
                // Reuse the Series container as well as the cell scratch buffer.
                for row in slice.list()?.amortized_iter() {
                    match row {
                        Some(row) => {
                            cells.clear();
                            for_each_index::<CellIndex, _>(row.as_ref(), "h3 cell", |cell| {
                                if let Some(cell) = cell {
                                    cells.push(cell);
                                }
                            })?;
                            op(&mut cells, &mut builder)?;
                        },
                        None => builder.append_null(),
                    }
                }
            } else {
                for_each_index::<CellIndex, _>(cell_series, "h3 cell", |cell| {
                    if let Some(cell) = cell {
                        cells.push(cell);
                    }
                })?;
                op(&mut cells, &mut builder)?;
            }
            Ok(builder.finish().into_series())
        },
    )?;
    // Assemble numeric batches before converting: an all-null batch must not
    // introduce List(Null) into an otherwise typed list column.
    match target_dtype {
        DataType::UInt64 => Ok(output),
        DataType::Int64 => output.cast(&DataType::List(Box::new(DataType::Int64))),
        _ => cast_list_u64_to_dtype(&output, &DataType::UInt64, Some(&target_dtype)),
    }
}

pub fn compact_cells(cell_series: &Series) -> PolarsResult<Series> {
    map_cell_sets(cell_series, |cells, builder| {
        CellIndex::compact(cells)
            .map_err(|e| PolarsError::ComputeError(format!("Compaction error: {}", e).into()))?;
        builder.append_values_iter(cells.iter().copied().map(u64::from));
        Ok(())
    })
}

pub fn uncompact_cells(cell_series: &Series, res: u8) -> PolarsResult<Series> {
    let target_res = Resolution::try_from(res)
        .map_err(|_| PolarsError::ComputeError("Invalid resolution".into()))?;
    map_cell_sets(cell_series, |cells, builder| {
        builder.append_values_iter(
            CellIndex::uncompact(cells.iter().copied(), target_res).map(u64::from),
        );
        Ok(())
    })
}
