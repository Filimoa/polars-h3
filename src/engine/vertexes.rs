use h3o::{LatLng, Vertex, VertexIndex};
use polars::prelude::*;

use super::utils::{map_cell_lists, map_cells, map_index_lists, map_indices_with_min};

pub fn cell_to_vertex(cell_series: &Series, vertex_num: u8) -> PolarsResult<Series> {
    // Try to create vertex first to validate the number
    let vertex = Vertex::try_from(vertex_num).map_err(|_| {
        PolarsError::ComputeError(format!("Invalid vertex number: {}", vertex_num).into())
    })?;

    map_cells::<UInt64Type, _, _>(cell_series, |cell| {
        cell.and_then(|idx| idx.vertex(vertex).map(Into::into))
    })
}

pub fn cell_to_vertexes(cell_series: &Series) -> PolarsResult<Series> {
    map_cell_lists(cell_series, 6, |cell, builder| {
        builder.append_values_iter(cell.vertexes().map(u64::from));
    })
}

pub fn vertex_to_latlng(vertex_series: &Series) -> PolarsResult<Series> {
    map_index_lists::<VertexIndex, Float64Type, _>(
        vertex_series,
        "vertex",
        2,
        1024,
        |idx, builder| {
            let coord = LatLng::from(idx);
            builder.append_slice(&[coord.lat(), coord.lng()]);
        },
    )
}

pub fn is_valid_vertex(vertex_series: &Series) -> PolarsResult<Series> {
    map_indices_with_min::<VertexIndex, BooleanType, _, _>(
        vertex_series,
        "vertex",
        1024,
        |vertex| Some(vertex.is_some()),
    )
}
