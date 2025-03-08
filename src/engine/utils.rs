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

// A function that takes N float64 Series columns, and for each row:
//   - If all columns are non-null, gather them into a Vec<f64>
//   - Pass that slice to the user-supplied closure `row_fn` -> Option<T>
//   - If any column is null in that row, row result is None
// Collects into a Vec<Option<T>>.

pub fn parse_multi_f64_columns<T, F>(
    columns: &[&Series],
    mut row_fn: F,
) -> PolarsResult<Vec<Option<T>>>
where
    F: FnMut(&[f64]) -> Option<T> + Send + Sync,
    T: Send,
{
    // 1) Coerce all columns to Float64
    let float_cols: Vec<Float64Chunked> = columns
        .iter()
        .map(|s| s.cast(&DataType::Float64)?.f64().map(|ca| ca.clone()))
        .collect::<PolarsResult<Vec<_>>>()?;

    // 2) We'll assume all series have same length
    let len = float_cols[0].len();
    for c in &float_cols {
        if c.len() != len {
            return Err(PolarsError::ComputeError(
                "All columns must have the same length".into(),
            ));
        }
    }

    // 3) Convert each Float64Chunked into an Iterator<Option<f64>> for row by row
    let iters: Vec<_> = float_cols.iter().map(|c| c.into_iter()).collect();

    // We can't trivially zip many iterators in stable Rust, so we gather them row-by-row.
    // (Or you could use `itertools::multizip`, but let's do a straightforward approach.)

    // We'll collect each column's values into a Vec<Vec<Option<f64>>> so we can access row i from each col easily.
    // Alternatively we can do chunked arrow merges or similar, but let's keep it simple.

    // Flatten each chunked array into a single Vec<Option<f64>>
    let col_values: Vec<Vec<Option<f64>>> = iters.into_iter().map(|iter| iter.collect()).collect();

    // col_values[c][row] => the Option<f64> for column c, row i

    // 4) For each row, check all columns
    let out: Vec<Option<T>> = (0..len)
        .into_iter()
        .map(|i| {
            // gather floats from each column c at row i
            let mut row_floats = Vec::with_capacity(columns.len());
            for col_c in 0..columns.len() {
                match col_values[col_c][i] {
                    Some(val) => row_floats.push(val),
                    // If any is null => entire row is None
                    None => return None,
                }
            }
            // If we get here, no column was null; pass them to row_fn
            row_fn(&row_floats)
        })
        .collect();

    Ok(out)
}
