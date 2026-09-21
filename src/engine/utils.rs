use h3o::{CellIndex, DirectedEdgeIndex, VertexIndex};
use polars::error::PolarsResult;
use polars::prelude::*;
use rayon::prelude::*;

pub fn parse_cell_indices(cell_series: &Series) -> PolarsResult<Vec<Option<CellIndex>>> {
    map_cell_indices(cell_series, std::convert::identity)
}

/// Validate cells while consuming them, without materializing an intermediate column.
/// Collecting serially also avoids Rayon producing an array for every small task.
pub fn map_cell_indices<B, T, F>(cell_series: &Series, mut op: F) -> PolarsResult<B>
where
    B: FromIterator<T>,
    F: FnMut(Option<CellIndex>) -> T,
{
    Ok(match cell_series.dtype() {
        DataType::UInt64 => cell_series
            .u64()?
            .iter()
            .map(|opt| opt.and_then(|v| CellIndex::try_from(v).ok()))
            .map(&mut op)
            .collect(),
        DataType::Int64 => cell_series
            .i64()?
            .iter()
            .map(|opt| opt.and_then(|v| CellIndex::try_from(v as u64).ok()))
            .map(&mut op)
            .collect(),
        DataType::String => cell_series
            .str()?
            .iter()
            .map(|opt| {
                opt.and_then(|s| u64::from_str_radix(s, 16).ok())
                    .and_then(|v| CellIndex::try_from(v).ok())
            })
            .map(&mut op)
            .collect(),
        _ => {
            return Err(PolarsError::ComputeError(
                format!("Unsupported type for h3 cell: {:?}", cell_series.dtype()).into(),
            ))
        },
    })
}

fn map_indices<I, B, T, F>(cell_series: &Series, kind: &str, mut op: F) -> PolarsResult<B>
where
    I: TryFrom<u64>,
    B: FromIterator<T>,
    F: FnMut(Option<I>) -> T,
{
    Ok(match cell_series.dtype() {
        DataType::UInt64 => cell_series
            .u64()?
            .iter()
            .map(|opt| opt.and_then(|v| I::try_from(v).ok()))
            .map(&mut op)
            .collect(),
        DataType::Int64 => cell_series
            .i64()?
            .iter()
            .map(|opt| opt.and_then(|v| I::try_from(v as u64).ok()))
            .map(&mut op)
            .collect(),
        DataType::String => cell_series
            .str()?
            .iter()
            .map(|opt| {
                opt.and_then(|s| u64::from_str_radix(s, 16).ok())
                    .and_then(|v| I::try_from(v).ok())
            })
            .map(&mut op)
            .collect(),
        _ => {
            return Err(PolarsError::ComputeError(
                format!("Unsupported type for {}: {:?}", kind, cell_series.dtype()).into(),
            ))
        },
    })
}

pub fn map_edge_indices<B, T, F>(series: &Series, op: F) -> PolarsResult<B>
where
    B: FromIterator<T>,
    F: FnMut(Option<DirectedEdgeIndex>) -> T,
{
    map_indices(series, "edge", op)
}

pub fn map_vertex_indices<B, T, F>(series: &Series, op: F) -> PolarsResult<B>
where
    B: FromIterator<T>,
    F: FnMut(Option<VertexIndex>) -> T,
{
    map_indices(series, "vertex", op)
}

/// Borrow the second cell column of a paired operation without copying it.
/// Each iterator advances through its own Arrow chunks, so boundaries may differ.
pub fn cell_index_iter(
    series: &Series,
) -> PolarsResult<Box<dyn Iterator<Item = Option<CellIndex>> + '_>> {
    Ok(match series.dtype() {
        DataType::UInt64 => Box::new(
            series
                .u64()?
                .iter()
                .map(|v| v.and_then(|v| CellIndex::try_from(v).ok())),
        ) as Box<dyn Iterator<Item = Option<CellIndex>>>,
        DataType::Int64 => Box::new(
            series
                .i64()?
                .iter()
                .map(|v| v.and_then(|v| CellIndex::try_from(v as u64).ok())),
        ),
        DataType::String => Box::new(series.str()?.iter().map(|v| {
            v.and_then(|v| u64::from_str_radix(v, 16).ok())
                .and_then(|v| CellIndex::try_from(v).ok())
        })),
        _ => polars_bail!(ComputeError: "Unsupported type for h3 cell: {:?}", series.dtype()),
    })
}

/// Cheap kernels keep ordinary Polars partitions serial but split large calls.
pub fn apply_scalar_batches<F>(series: &Series, op: F) -> PolarsResult<Series>
where
    F: Fn(&Series) -> PolarsResult<Series> + Sync,
{
    if series.len() < 262_144 {
        op(series)
    } else {
        apply_batches(series.len(), |offset, len| {
            op(&series.slice(offset as i64, len))
        })
    }
}

/// Format directly into Arrow storage using one reusable buffer per builder.
pub struct HexStringBuilder {
    builder: StringChunkedBuilder,
    buffer: String,
}

impl HexStringBuilder {
    pub fn new(capacity: usize) -> Self {
        Self {
            builder: StringChunkedBuilder::new(PlSmallStr::EMPTY, capacity),
            buffer: String::with_capacity(16),
        }
    }

    pub fn append(&mut self, value: Option<u64>) {
        use std::fmt::Write;
        match value {
            Some(value) => {
                self.buffer.clear();
                write!(&mut self.buffer, "{value:x}").expect("writing to a String cannot fail");
                self.builder.append_value(&self.buffer);
            },
            None => self.builder.append_null(),
        }
    }

    pub fn finish(self) -> StringChunked {
        self.builder.finish()
    }
}

/// Parallelize expensive kernels in ordered batches, each producing one column.
/// Small calls stay on the caller thread, including batches already split by Polars.
pub fn apply_batches<F>(len: usize, op: F) -> PolarsResult<Series>
where
    F: Fn(usize, usize) -> PolarsResult<Series> + Sync,
{
    // The activation threshold avoids nested work for small Polars partitions;
    // smaller batches above it keep medium coordinate inputs parallel as well.
    const MIN_PARALLEL_SIZE: usize = 4_096;
    const MIN_BATCH_SIZE: usize = 1_024;
    if len < MIN_PARALLEL_SIZE {
        return op(0, len);
    }
    let n_batches = (len / MIN_BATCH_SIZE).min(rayon::current_num_threads());
    if n_batches <= 1 {
        return op(0, len);
    }

    let batch_size = len.div_ceil(n_batches);
    let batches: PolarsResult<Vec<_>> = (0..n_batches)
        .into_par_iter()
        .map(|batch| {
            let offset = batch * batch_size;
            op(offset, batch_size.min(len - offset))
        })
        .collect();
    let mut batches = batches?.into_iter();
    let mut output = batches.next().expect("at least two batches");
    for batch in batches {
        output.append(&batch)?;
    }
    Ok(output)
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
        DataType::String => {
            let mut builder = HexStringBuilder::new(result.len());
            for value in result.iter() {
                builder.append(value);
            }
            Ok(builder.finish().into_series())
        },
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
                            let mut builder = HexStringBuilder::new(u64_ca.len());
                            for value in u64_ca.iter() {
                                builder.append(value);
                            }
                            Ok(builder.finish().into_series())
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
