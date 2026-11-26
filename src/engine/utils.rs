use h3o::CellIndex;
use polars::error::PolarsResult;
use polars::prelude::*;
use rayon::prelude::*;
use std::fmt::Write;

/// Process bounded batches, retaining one Arrow chunk per batch. Collecting
/// individual rows through Rayon's Polars collector can produce thousands of
/// tiny chunks, making subsequent expressions and Arrow export expensive.
pub fn parallel_chunks<F>(len: usize, op: F) -> PolarsResult<Series>
where
    F: Fn(usize, usize) -> PolarsResult<Series> + Sync + Send,
{
    parallel_chunks_with_min(len, 16_384, op)
}

/// Expensive rows need smaller batches than simple scalar transforms. Keep the
/// maximum batch size unchanged so large outputs still have bounded chunk counts.
pub fn parallel_chunks_with_min<F>(len: usize, min_batch_size: usize, op: F) -> PolarsResult<Series>
where
    F: Fn(usize, usize) -> PolarsResult<Series> + Sync + Send,
{
    const MAX_BATCH_SIZE: usize = 65_536;
    let min_batch_size = min_batch_size.clamp(1, MAX_BATCH_SIZE);
    if len <= min_batch_size {
        return op(0, len);
    }
    // Round the number of batches to a multiple of the worker count. Simply
    // clamping batch sizes can leave workers idle (100K rows / 16K = 7 batches
    // on an 8-worker pool), which hurts compute-heavy operations.
    let workers = rayon::current_num_threads();
    let desired_batches = len.div_ceil(min_batch_size).min(workers * 4);
    let batches = desired_batches
        .max(len.div_ceil(MAX_BATCH_SIZE))
        .div_ceil(workers)
        * workers;
    let batch_size = len.div_ceil(batches);
    let chunks: PolarsResult<Vec<_>> = (0..len.div_ceil(batch_size))
        .into_par_iter()
        .map(|batch| {
            let offset = batch * batch_size;
            op(offset, batch_size.min(len - offset))
        })
        .collect();
    let mut chunks = chunks?.into_iter();
    let mut result = chunks.next().expect("nonempty batch list");
    for chunk in chunks {
        result.append(&chunk)?;
    }
    Ok(result)
}

/// Validate and transform cells in one pass, without a column-sized scratch
/// vector. Integer, string, null and invalid-value behavior matches parsing.
pub fn map_cells<T, R, F>(series: &Series, op: F) -> PolarsResult<Series>
where
    T: PolarsDataType,
    ChunkedArray<T>: FromIterator<Option<R>> + IntoSeries,
    F: Fn(Option<CellIndex>) -> Option<R> + Sync + Send,
{
    map_indices::<CellIndex, T, R, F>(series, "h3 cell", op)
}

pub fn map_indices<I, T, R, F>(series: &Series, kind: &str, op: F) -> PolarsResult<Series>
where
    I: TryFrom<u64>,
    T: PolarsDataType,
    ChunkedArray<T>: FromIterator<Option<R>> + IntoSeries,
    F: Fn(Option<I>) -> Option<R> + Sync + Send,
{
    map_indices_with_min::<I, T, R, F>(series, kind, 16_384, op)
}

pub fn map_indices_with_min<I, T, R, F>(
    series: &Series,
    kind: &str,
    min_batch_size: usize,
    op: F,
) -> PolarsResult<Series>
where
    I: TryFrom<u64>,
    T: PolarsDataType,
    ChunkedArray<T>: FromIterator<Option<R>> + IntoSeries,
    F: Fn(Option<I>) -> Option<R> + Sync + Send,
{
    parallel_chunks_with_min(series.len(), min_batch_size, |offset, len| {
        let slice = series.slice(offset as i64, len);
        let out: ChunkedArray<T> = match slice.dtype() {
            DataType::UInt64 => slice
                .u64()?
                .iter()
                .map(|v| op(v.and_then(|v| I::try_from(v).ok())))
                .collect(),
            DataType::Int64 => slice
                .i64()?
                .iter()
                .map(|v| op(v.and_then(|v| I::try_from(v as u64).ok())))
                .collect(),
            DataType::String => slice
                .str()?
                .iter()
                .map(|v| {
                    op(v.and_then(|s| u64::from_str_radix(s, 16).ok())
                        .and_then(|v| I::try_from(v).ok()))
                })
                .collect(),
            _ => polars_bail!(ComputeError: "Unsupported type for {}: {:?}", kind, slice.dtype()),
        };
        Ok(out.into_series())
    })
}

/// Keep binary-operation validation and scratch storage local to each batch.
pub fn map_cell_pairs<T, R, F>(left: &Series, right: &Series, op: F) -> PolarsResult<Series>
where
    T: PolarsDataType,
    ChunkedArray<T>: FromIterator<Option<R>> + IntoSeries,
    F: Fn(Option<CellIndex>, Option<CellIndex>) -> Option<R> + Sync + Send,
{
    parallel_chunks(left.len().min(right.len()), |offset, len| {
        let lhs = parse_cell_indices(&left.slice(offset as i64, len))?;
        let rhs = parse_cell_indices(&right.slice(offset as i64, len))?;
        let result: ChunkedArray<T> = lhs.into_iter().zip(rhs).map(|(a, b)| op(a, b)).collect();
        Ok(result.into_series())
    })
}

/// Append list values directly into a batch's Arrow buffers, avoiding a heap
/// allocation for every row and a later serial copy of all list contents.
pub fn map_cell_lists<F>(series: &Series, values_per_cell: usize, op: F) -> PolarsResult<Series>
where
    F: Fn(CellIndex, &mut ListPrimitiveChunkedBuilder<UInt64Type>) + Sync + Send,
{
    map_index_lists::<CellIndex, UInt64Type, _>(series, "h3 cell", values_per_cell, 16_384, op)
}

/// Visit validated IDs without materializing a temporary column.
pub fn for_each_index<I, F>(series: &Series, kind: &str, mut op: F) -> PolarsResult<()>
where
    I: TryFrom<u64>,
    F: FnMut(Option<I>),
{
    match series.dtype() {
        DataType::UInt64 => series
            .u64()?
            .iter()
            .for_each(|v| op(v.and_then(|v| I::try_from(v).ok()))),
        DataType::Int64 => series
            .i64()?
            .iter()
            .for_each(|v| op(v.and_then(|v| I::try_from(v as u64).ok()))),
        DataType::String => series.str()?.iter().for_each(|v| {
            op(v.and_then(|s| u64::from_str_radix(s, 16).ok())
                .and_then(|v| I::try_from(v).ok()))
        }),
        _ => polars_bail!(ComputeError: "Unsupported type for {}: {:?}", kind, series.dtype()),
    }
    Ok(())
}

pub fn map_index_lists<I, T, F>(
    series: &Series,
    kind: &str,
    values_per_row: usize,
    min_batch_size: usize,
    op: F,
) -> PolarsResult<Series>
where
    I: TryFrom<u64>,
    T: PolarsNumericType,
    F: Fn(I, &mut ListPrimitiveChunkedBuilder<T>) + Sync + Send,
{
    parallel_chunks_with_min(series.len(), min_batch_size, |offset, len| {
        let mut builder = ListPrimitiveChunkedBuilder::<T>::new(
            PlSmallStr::EMPTY,
            len,
            len * values_per_row,
            T::get_static_dtype(),
        );
        for_each_index::<I, _>(
            &series.slice(offset as i64, len),
            kind,
            |value| match value {
                Some(value) => op(value, &mut builder),
                None => builder.append_null(),
            },
        )?;
        Ok(builder.finish().into_series())
    })
}

pub fn parse_cell_indices(cell_series: &Series) -> PolarsResult<Vec<Option<CellIndex>>> {
    Ok(match cell_series.dtype() {
        DataType::UInt64 => cell_series
            .u64()?
            .iter()
            .map(|opt| opt.and_then(|v| CellIndex::try_from(v).ok()))
            .collect(),
        DataType::Int64 => cell_series
            .i64()?
            .iter()
            .map(|opt| opt.and_then(|v| CellIndex::try_from(v as u64).ok()))
            .collect(),
        DataType::String => cell_series
            .str()?
            .iter()
            .map(|opt| {
                opt.and_then(|s| u64::from_str_radix(s, 16).ok())
                    .and_then(|v| CellIndex::try_from(v).ok())
            })
            .collect(),
        _ => {
            return Err(PolarsError::ComputeError(
                format!("Unsupported type for h3 cell: {:?}", cell_series.dtype()).into(),
            ))
        },
    })
}

pub fn cast_u64_to_dtype(
    original_dtype: &DataType,
    target_dtype: Option<&DataType>,
    result: UInt64Chunked,
) -> PolarsResult<Series> {
    let final_dtype = target_dtype.unwrap_or(original_dtype);

    match final_dtype {
        DataType::UInt64 => Ok(result.into_series()),
        DataType::Int64 => result.cast(&DataType::Int64),
        DataType::String => parallel_chunks(result.len(), |offset, len| {
            let slice = result.slice(offset as i64, len);
            let values = slice.rechunk();
            Ok(values
                .apply_into_string_amortized(|value, buffer| {
                    write!(buffer, "{value:x}").expect("writing into a String cannot fail");
                })
                .into_series())
        }),
        _ => polars_bail!(ComputeError: "Unsupported dtype for H3 result"),
    }
}

pub fn cast_list_u64_to_dtype(
    list_series: &Series,
    original_dtype: &DataType,
    target_dtype: Option<&DataType>,
) -> PolarsResult<Series> {
    // The previous per-row collector inferred List(Null) when no row was valid.
    // Preserve that legacy dtype for empty/all-null outputs.
    if list_series.null_count() == list_series.len() {
        return Ok(Series::full_null(
            PlSmallStr::EMPTY,
            list_series.len(),
            &DataType::List(Box::new(DataType::Null)),
        ));
    }
    let final_dtype = target_dtype.unwrap_or(original_dtype);
    parallel_chunks(list_series.len(), |offset, len| {
        let slice = list_series.slice(offset as i64, len);
        Ok(slice
            .list()?
            .apply_to_inner(&|values| {
                let values = values.cast(&DataType::UInt64)?;
                cast_u64_to_dtype(&DataType::UInt64, Some(final_dtype), values.u64()?.clone())
            })?
            .into_series())
    })
}

pub fn list_u64_vecs_to_series(
    name: PlSmallStr,
    values: Vec<Option<Vec<u64>>>,
    target_inner_dtype: &DataType,
) -> PolarsResult<Series> {
    let values_capacity = values
        .iter()
        .filter_map(|opt| opt.as_ref().map(Vec::len))
        .sum();
    let mut builder = ListPrimitiveChunkedBuilder::<UInt64Type>::new(
        name,
        values.len(),
        values_capacity,
        DataType::UInt64,
    );

    for opt_values in values {
        match opt_values {
            Some(values) => builder.append_slice(&values),
            None => builder.append_null(),
        }
    }

    let out = builder.finish().into_series();
    match target_inner_dtype {
        DataType::UInt64 => Ok(out),
        DataType::Int64 => out.cast(&DataType::List(Box::new(DataType::Int64))),
        DataType::String => {
            cast_list_u64_to_dtype(&out, &DataType::UInt64, Some(target_inner_dtype))
        },
        _ => polars_bail!(ComputeError: "Unsupported dtype for H3 List result"),
    }
}

pub fn resolve_target_inner_dtype(original_dtype: &DataType) -> PolarsResult<DataType> {
    // If the original was a List, extract its inner type. Otherwise, use the original directly.
    let inner_original_dtype = match original_dtype {
        DataType::List(inner) => *inner.clone(),
        dt => dt.clone(),
    };

    let target_inner_dtype = match inner_original_dtype {
        DataType::UInt64 => DataType::UInt64,
        DataType::Int64 => DataType::Int64,
        DataType::String => DataType::String,
        other => {
            return Err(PolarsError::ComputeError(
                format!("Unsupported inner dtype: {:?}", other).into(),
            ))
        },
    };

    Ok(target_inner_dtype)
}

/// Return an error if `series` has any nulls.
pub fn bail_if_null(series: &Series, context: &str) -> PolarsResult<()> {
    if series.null_count() > 0 {
        return Err(PolarsError::ComputeError(
            format!("Null values not allowed in {}", context).into(),
        ));
    }
    Ok(())
}

/// Return an error if *any* of the provided Series have nulls.
///
/// - `checks` is a slice of `(Series, &str)` pairs,
///   where each &str is the "context" or name used in error messages.
pub fn bail_if_null_many(checks: &[(&Series, &str)]) -> PolarsResult<()> {
    for (series, context) in checks {
        if series.null_count() > 0 {
            return Err(PolarsError::ComputeError(
                format!("Null values not allowed in {}", context).into(),
            ));
        }
    }
    Ok(())
}
