use h3o::{LatLng, Vertex, VertexIndex};
use polars::prelude::*;
use rayon::prelude::*;

use super::utils::{
    apply_batches, apply_scalar_batches, list_u64_vecs_to_series, map_cell_indices,
    map_vertex_indices, parse_cell_indices,
};

pub fn cell_to_vertex(cell_series: &Series, vertex_num: u8) -> PolarsResult<Series> {
    // Try to create vertex first to validate the number
    let vertex = Vertex::try_from(vertex_num).map_err(|_| {
        PolarsError::ComputeError(format!("Invalid vertex number: {}", vertex_num).into())
    })?;

    apply_batches(cell_series.len(), |offset, len| {
        let cells = cell_series.slice(offset as i64, len);
        let vertices: UInt64Chunked = map_cell_indices(&cells, |cell| {
            cell.and_then(|idx| idx.vertex(vertex).map(Into::into))
        })?;
        Ok(vertices.into_series())
    })
}

pub fn cell_to_vertexes(cell_series: &Series) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let vertex_lists: Vec<Option<Vec<u64>>> = cells
        .into_par_iter()
        .map(|cell| cell.map(|idx| idx.vertexes().map(Into::into).collect()))
        .collect();

    list_u64_vecs_to_series(PlSmallStr::from(""), vertex_lists, &DataType::UInt64)
}

pub fn vertex_to_latlng(vertex_series: &Series) -> PolarsResult<Series> {
    // Parse vertex indices from various input types
    let vertices: Vec<Option<VertexIndex>> = match vertex_series.dtype() {
        DataType::UInt64 => vertex_series
            .u64()?
            .iter()
            .map(|opt| opt.and_then(|v| VertexIndex::try_from(v).ok()))
            .collect(),
        DataType::Int64 => vertex_series
            .i64()?
            .iter()
            .map(|opt| opt.and_then(|v| VertexIndex::try_from(v as u64).ok()))
            .collect(),
        DataType::String => vertex_series
            .str()?
            .iter()
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

    let coords: Vec<Option<[f64; 2]>> = vertices
        .into_par_iter()
        .map(|vertex| {
            vertex.map(|idx| {
                let latlng = LatLng::from(idx);
                [latlng.lat(), latlng.lng()]
            })
        })
        .collect();

    let mut builder = ListPrimitiveChunkedBuilder::<Float64Type>::new(
        PlSmallStr::from(""),
        coords.len(),
        coords.len() * 2,
        DataType::Float64,
    );
    for opt_coord in coords {
        match opt_coord {
            Some(coord) => builder.append_slice(&coord),
            None => builder.append_null(),
        }
    }

    Ok(builder.finish().into_series())
}

pub fn is_valid_vertex(vertex_series: &Series) -> PolarsResult<Series> {
    apply_scalar_batches(vertex_series, |vertices| {
        let valid: BooleanChunked = map_vertex_indices(vertices, |vertex| vertex.is_some())?;
        Ok(valid.into_series())
    })
}
