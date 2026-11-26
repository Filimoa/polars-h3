use polars::prelude::*;
use rayon::prelude::*;

use super::utils::{map_cells, parse_cell_indices};

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
    map_cells::<StringType, _, _>(cell_series, |cell| cell.map(|c| c.to_string()))
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
    let cells = parse_cell_indices(cell_series)?;

    let faces: Vec<Option<Vec<i64>>> = cells
        .into_par_iter()
        .map(|cell| {
            cell.map(|idx| {
                let faces = idx.icosahedron_faces();
                faces.iter().map(|f| u8::from(f) as i64).collect()
            })
        })
        .collect();

    let values_capacity = faces
        .iter()
        .filter_map(|opt| opt.as_ref().map(Vec::len))
        .sum();
    let mut builder = ListPrimitiveChunkedBuilder::<Int64Type>::new(
        PlSmallStr::from(""),
        faces.len(),
        values_capacity,
        DataType::Int64,
    );
    for opt_faces in faces {
        match opt_faces {
            Some(faces) => builder.append_slice(&faces),
            None => builder.append_null(),
        }
    }

    Ok(builder.finish().into_series())
}
