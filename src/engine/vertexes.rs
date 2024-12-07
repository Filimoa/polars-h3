use h3o::{LatLng, Vertex, VertexIndex};
use polars::prelude::*;
use rayon::prelude::*;

use super::utils::parse_cell_indices;

pub fn cell_to_vertex(cell_series: &Series, vertex_num: u8) -> PolarsResult<Series> {
    // Try to create vertex first to validate the number
    let vertex = Vertex::try_from(vertex_num).map_err(|_| {
        PolarsError::ComputeError(format!("Invalid vertex number: {}", vertex_num).into())
    })?;

    let cells = parse_cell_indices(cell_series)?;

    let vertices: UInt64Chunked = cells
        .into_par_iter()
        .map(|cell| cell.and_then(|idx| idx.vertex(vertex).map(Into::into)))
        .collect();

    Ok(vertices.into_series())
}

pub fn cell_to_vertexes(cell_series: &Series) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let vertex_lists: ListChunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.map(|idx| {
                let vertices: Vec<u64> = idx.vertexes().map(Into::into).collect();
                Series::new(PlSmallStr::from(""), vertices.as_slice())
            })
        })
        .collect();

    Ok(vertex_lists.into_series())
}

pub fn vertex_to_latlng(vertex_series: &Series) -> PolarsResult<Series> {
    // Parse vertex indices from various input types
    let vertices: Vec<Option<VertexIndex>> = match vertex_series.dtype() {
        DataType::UInt64 => vertex_series
            .u64()?
            .into_iter()
            .map(|opt| opt.and_then(|v| VertexIndex::try_from(v).ok()))
            .collect(),
        DataType::Int64 => vertex_series
            .i64()?
            .into_iter()
            .map(|opt| opt.and_then(|v| VertexIndex::try_from(v as u64).ok()))
            .collect(),
        DataType::String => vertex_series
            .str()?
            .into_iter()
            .map(|opt| {
                opt.and_then(|s| u64::from_str_radix(s, 16).ok())
                    .and_then(|v| VertexIndex::try_from(v).ok())
            })
            .collect(),
        _ => {
            return Err(PolarsError::ComputeError(
                format!("Unsupported type for vertex: {:?}", vertex_series.dtype()).into(),
            ))
        },
    };

    let coords: ListChunked = vertices
        .into_par_iter()
        .map(|vertex| {
            vertex.map(|idx| {
                let latlng = LatLng::from(idx);
                Series::new(PlSmallStr::from(""), &[latlng.lat(), latlng.lng()])
            })
        })
        .collect();

    Ok(coords.into_series())
}

pub fn is_valid_vertex(vertex_series: &Series) -> PolarsResult<Series> {
    let is_valid = match vertex_series.dtype() {
        DataType::UInt64 => vertex_series
            .u64()?
            .into_iter()
            .map(|opt| {
                opt.map(|v| VertexIndex::try_from(v).is_ok())
                    .unwrap_or(false)
            })
            .collect::<BooleanChunked>(),
        DataType::Int64 => vertex_series
            .i64()?
            .into_iter()
            .map(|opt| {
                opt.map(|v| VertexIndex::try_from(v as u64).is_ok())
                    .unwrap_or(false)
            })
            .collect::<BooleanChunked>(),
        DataType::String => vertex_series
            .str()?
            .into_iter()
            .map(|opt| {
                opt.and_then(|s| u64::from_str_radix(s, 16).ok())
                    .map(|v| VertexIndex::try_from(v).is_ok())
                    .unwrap_or(false)
            })
            .collect::<BooleanChunked>(),
        _ => {
            return Err(PolarsError::ComputeError(
                format!("Unsupported type for vertex: {:?}", vertex_series.dtype()).into(),
            ))
        },
    };

    Ok(is_valid.into_series())
}
