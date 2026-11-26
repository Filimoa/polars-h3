use h3o::CellIndex;
use polars::prelude::*;

use super::utils::{cast_u64_to_dtype, map_cells, map_index_lists};

pub fn get_resolution(cell_series: &Series) -> PolarsResult<Series> {
    map_cells::<UInt32Type, _, _>(cell_series, |cell| {
        cell.map(|c| u8::from(c.resolution()) as u32)
    })
}

pub fn str_to_int(cell_series: &Series) -> PolarsResult<Series> {
    cell_series.str()?;
    map_cells::<UInt64Type, _, _>(cell_series, |cell| cell.map(Into::into))
}

pub fn int_to_str(cell_series: &Series) -> PolarsResult<Series> {
    if !matches!(cell_series.dtype(), DataType::UInt64 | DataType::Int64) {
        polars_bail!(ComputeError: "Expected UInt64 or Int64, got: {:?}", cell_series.dtype());
    }
    let values = map_cells::<UInt64Type, _, _>(cell_series, |cell| cell.map(u64::from))?;
    cast_u64_to_dtype(
        &DataType::UInt64,
        Some(&DataType::String),
        values.u64()?.clone(),
    )
}

pub fn is_valid_cell(cell_series: &Series) -> PolarsResult<Series> {
    map_cells::<BooleanType, _, _>(cell_series, |cell| Some(cell.is_some()))
}

pub fn is_pentagon(cell_series: &Series) -> PolarsResult<Series> {
    map_cells::<BooleanType, _, _>(cell_series, |cell| {
        Some(cell.is_some_and(|idx| idx.is_pentagon()))
    })
}

#[allow(non_snake_case)]
pub fn is_res_class_III(cell_series: &Series) -> PolarsResult<Series> {
    map_cells::<BooleanType, _, _>(cell_series, |cell| {
        Some(cell.is_some_and(|idx| idx.resolution().is_class3()))
    })
}

pub fn get_icosahedron_faces(cell_series: &Series) -> PolarsResult<Series> {
    map_index_lists::<CellIndex, Int64Type, _>(cell_series, "h3 cell", 2, 1024, |idx, builder| {
        builder.append_values_iter(idx.icosahedron_faces().iter().map(|f| u8::from(f) as i64));
    })
}
