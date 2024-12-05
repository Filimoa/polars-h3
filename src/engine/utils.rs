use h3o::CellIndex;
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
