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
    const MIN_BATCH_SIZE: usize = 16_384;
    const MAX_BATCH_SIZE: usize = 65_536;
    if len <= MIN_BATCH_SIZE {
        return op(0, len);
    }
    // Round the number of batches to a multiple of the worker count. Simply
    // clamping batch sizes can leave workers idle (100K rows / 16K = 7 batches
    // on an 8-worker pool), which hurts compute-heavy operations.
    let workers = rayon::current_num_threads();
    let desired_batches = len.div_ceil(MIN_BATCH_SIZE).min(workers * 4);
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
    parallel_chunks(series.len(), |offset, len| {
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
    parallel_chunks(series.len(), |offset, len| {
        let cells = parse_cell_indices(&series.slice(offset as i64, len))?;
        let mut builder = ListPrimitiveChunkedBuilder::<UInt64Type>::new(
            PlSmallStr::EMPTY,
            len,
            len * values_per_cell,
            DataType::UInt64,
        );
        for cell in cells {
            match cell {
                Some(cell) => op(cell, &mut builder),
                None => builder.append_null(),
            }
        }
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
    let ca = list_series.list()?;
    let final_dtype = target_dtype.unwrap_or(original_dtype);

    let out: ListChunked = ca
        .series_iter()
        .map(|opt_s| {
            opt_s
                .map(|s| {
                    // If the inner list isn't UInt64, cast it to UInt64.
                    let s_u64 = if s.dtype() != &DataType::UInt64 {
                        s.cast(&DataType::UInt64)?
                    } else {
                        s
                    };

                    let u64_ca = s_u64.u64()?;
                    match final_dtype {
                        DataType::UInt64 => {
                            // Create an owned version of the UInt64 chunked array before converting.
                            Ok(u64_ca.to_owned().into_series())
                        },
                        DataType::Int64 => u64_ca.cast(&DataType::Int64),
                        DataType::String => {
                            // Convert each u64 to a hex string.
                            let utf8: StringChunked = u64_ca
                                .iter()
                                .map(|opt_u| opt_u.map(|u| format!("{:x}", u)))
                                .collect();
                            Ok(utf8.into_series())
                        },
                        _ => polars_bail!(ComputeError: "Unsupported dtype for H3 List result"),
                    }
                })
                .transpose()
        })
        .collect::<PolarsResult<_>>()?;

    Ok(out.into_series())
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
