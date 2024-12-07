use h3o::CellIndex;
use polars::prelude::*;
use rayon::prelude::*;

use super::utils::parse_cell_indices;

pub fn get_resolution(cell_series: &Series) -> PolarsResult<Series> {
    // Convert input to u64 regardless of input type
    let cells = parse_cell_indices(cell_series)?;

    let resolutions: UInt32Chunked = cells
        .into_par_iter()
        .map(|cell| cell.map(|c| u8::from(c.resolution()) as u32))
        .collect();

    Ok(resolutions.into_series())
}

pub fn str_to_int(cell_series: &Series) -> PolarsResult<Series> {
    let str_ca = cell_series.str()?;

    let indices: UInt64Chunked = str_ca
        .into_iter()
        .map(|opt_str| {
            opt_str
                .and_then(|s| u64::from_str_radix(s, 16).ok())
                .and_then(|v| CellIndex::try_from(v).ok())
                .map(Into::into)
        })
        .collect();

    Ok(indices.into_series())
}

pub fn int_to_str(cell_series: &Series) -> PolarsResult<Series> {
    let cells = match cell_series.dtype() {
        DataType::UInt64 => cell_series
            .u64()?
            .into_iter()
            .map(|opt| opt.and_then(|v| CellIndex::try_from(v).ok()))
            .collect::<Vec<_>>(),
        DataType::Int64 => cell_series
            .i64()?
            .into_iter()
            .map(|opt| opt.and_then(|v| CellIndex::try_from(v as u64).ok()))
            .collect::<Vec<_>>(),
        _ => {
            return Err(PolarsError::ComputeError(
                format!("Expected UInt64 or Int64, got: {:?}", cell_series.dtype()).into(),
            ))
        },
    };

    let strings: StringChunked = cells
        .into_iter()
        .map(|opt_cell| opt_cell.map(|cell| cell.to_string()))
        .collect();

    Ok(strings.into_series())
}

pub fn is_valid_cell(cell_series: &Series) -> PolarsResult<Series> {
    let is_valid = match cell_series.dtype() {
        DataType::UInt64 => cell_series
            .u64()?
            .into_iter()
            .map(|opt| opt.map(|v| CellIndex::try_from(v).is_ok()).unwrap_or(false))
            .collect::<BooleanChunked>(),
        DataType::Int64 => cell_series
            .i64()?
            .into_iter()
            .map(|opt| {
                opt.map(|v| CellIndex::try_from(v as u64).is_ok())
                    .unwrap_or(false)
            })
            .collect::<BooleanChunked>(),
        DataType::String => cell_series
            .str()?
            .into_iter()
            .map(|opt_str| {
                opt_str
                    .map(|s| {
                        u64::from_str_radix(s, 16)
                            .ok()
                            .and_then(|v| CellIndex::try_from(v).ok())
                            .is_some()
                    })
                    .unwrap_or(false)
            })
            .collect::<BooleanChunked>(),
        _ => {
            return Err(PolarsError::ComputeError(
                format!("Unsupported type for h3 cell: {:?}", cell_series.dtype()).into(),
            ))
        },
    };

    Ok(is_valid.into_series())
}

pub fn is_pentagon(cell_series: &Series) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let is_pent: BooleanChunked = cells
        .into_par_iter()
        .map(|cell| cell.map(|idx| idx.is_pentagon()).unwrap_or(false))
        .collect();

    Ok(is_pent.into_series())
}

#[allow(non_snake_case)]
pub fn is_res_class_III(cell_series: &Series) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let is_class3: BooleanChunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.map(|idx| idx.resolution().is_class3())
                .unwrap_or(false)
        })
        .collect();

    Ok(is_class3.into_series())
}

pub fn get_icosahedron_faces(cell_series: &Series) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let faces: ListChunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.map(|idx| {
                let faces = idx.icosahedron_faces();
                // Convert faces set to vec of integers
                Series::new(
                    PlSmallStr::from(""),
                    faces
                        .iter()
                        .map(|f| u8::from(f) as i64)
                        .collect::<Vec<_>>()
                        .as_slice(),
                )
            })
        })
        .collect();

    Ok(faces.into_series())
}
