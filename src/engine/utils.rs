use h3o::CellIndex;
use polars::error::PolarsResult;
use polars::prelude::*;

pub fn parse_cell_indices(cell_series: &Series) -> PolarsResult<Vec<Option<CellIndex>>> {
    Ok(match cell_series.dtype() {
        DataType::UInt64 => cell_series
            .u64()?
            .into_iter()
            .map(|opt| opt.and_then(|v| CellIndex::try_from(v).ok()))
            .collect(),
        DataType::Int64 => cell_series
            .i64()?
            .into_iter()
            .map(|opt| opt.and_then(|v| CellIndex::try_from(v as u64).ok()))
            .collect(),
        DataType::String => cell_series
            .str()?
            .into_iter()
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

fn broadcast_length(lengths: &[usize], context: &str) -> PolarsResult<usize> {
    let mut target_length = None;

    for &length in lengths {
        if length == 1 {
            continue;
        }

        match target_length {
            Some(target) if target != length => {
                polars_bail!(
                    ComputeError:
                    "Cannot broadcast input lengths {:?} in {}",
                    lengths,
                    context
                );
            },
            None => target_length = Some(length),
            _ => {},
        }
    }

    Ok(target_length.unwrap_or(1))
}

fn broadcast_values<T: Clone>(
    values: Vec<T>,
    target_length: usize,
    context: &str,
) -> PolarsResult<Vec<T>> {
    match values.len() {
        length if length == target_length => Ok(values),
        1 => Ok(vec![values[0].clone(); target_length]),
        length => {
            polars_bail!(
                ComputeError:
                "Cannot broadcast input of length {} to {} in {}",
                length,
                target_length,
                context
            );
        },
    }
}

pub fn broadcast_pair<T: Clone, U: Clone>(
    left: Vec<T>,
    right: Vec<U>,
    context: &str,
) -> PolarsResult<(Vec<T>, Vec<U>)> {
    let target_length = broadcast_length(&[left.len(), right.len()], context)?;
    Ok((
        broadcast_values(left, target_length, context)?,
        broadcast_values(right, target_length, context)?,
    ))
}

pub fn broadcast_triple<T: Clone, U: Clone, V: Clone>(
    first: Vec<T>,
    second: Vec<U>,
    third: Vec<V>,
    context: &str,
) -> PolarsResult<(Vec<T>, Vec<U>, Vec<V>)> {
    let target_length = broadcast_length(&[first.len(), second.len(), third.len()], context)?;
    Ok((
        broadcast_values(first, target_length, context)?,
        broadcast_values(second, target_length, context)?,
        broadcast_values(third, target_length, context)?,
    ))
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
            let utf8: StringChunked = result
                .into_iter()
                .map(|opt_u| opt_u.map(|u| format!("{:x}", u)))
                .collect();
            Ok(utf8.into_series())
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
        .into_iter()
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
                                .into_iter()
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
