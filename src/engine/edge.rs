use h3o::DirectedEdgeIndex;
use polars::prelude::*;

use super::utils::{map_cell_lists, map_cell_pairs, map_index_lists, map_indices};

pub fn are_neighbor_cells(
    origin_series: &Series,
    destination_series: &Series,
) -> PolarsResult<Series> {
    map_cell_pairs::<BooleanType, _, _>(origin_series, destination_series, |origin, dest| {
        Some(match (origin, dest) {
            (Some(org), Some(dst)) => org.is_neighbor_with(dst).ok().unwrap_or(false),
            _ => false,
        })
    })
}

pub fn cells_to_directed_edge(
    origin_series: &Series,
    destination_series: &Series,
) -> PolarsResult<Series> {
    map_cell_pairs::<UInt64Type, _, _>(origin_series, destination_series, |origin, dest| {
        match (origin, dest) {
            (Some(org), Some(dst)) => org.edge(dst).map(Into::into),
            _ => None,
        }
    })
}

pub fn is_valid_directed_edge(edge_series: &Series) -> PolarsResult<Series> {
    map_indices::<DirectedEdgeIndex, BooleanType, _, _>(edge_series, "edge", |edge| {
        Some(edge.is_some())
    })
}

pub fn get_directed_edge_origin(edge_series: &Series) -> PolarsResult<Series> {
    map_indices::<DirectedEdgeIndex, UInt64Type, _, _>(edge_series, "edge", |edge| {
        edge.map(|idx| u64::from(idx.origin()))
    })
}

pub fn get_directed_edge_destination(edge_series: &Series) -> PolarsResult<Series> {
    map_indices::<DirectedEdgeIndex, UInt64Type, _, _>(edge_series, "edge", |edge| {
        edge.map(|idx| u64::from(idx.destination()))
    })
}

pub fn directed_edge_to_cells(edge_series: &Series) -> PolarsResult<Series> {
    map_index_lists::<DirectedEdgeIndex, UInt64Type, _>(
        edge_series,
        "edge",
        2,
        16_384,
        |idx, builder| {
            builder.append_slice(&[u64::from(idx.origin()), u64::from(idx.destination())]);
        },
    )
}

pub fn origin_to_directed_edges(cell_series: &Series) -> PolarsResult<Series> {
    map_cell_lists(cell_series, 6, |cell, builder| {
        let mut edges = [0u64; 6];
        let mut len = 0;
        for edge in cell.edges() {
            edges[len] = u64::from(edge);
            len += 1;
        }
        edges[..len].sort_unstable();
        builder.append_slice(&edges[..len]);
    })
}

pub fn directed_edge_to_boundary(edge_series: &Series) -> PolarsResult<Series> {
    map_index_lists::<DirectedEdgeIndex, Float64Type, _>(
        edge_series,
        "edge",
        4,
        1024,
        |idx, builder| {
            let boundary = idx.boundary();
            builder
                .append_values_iter(boundary.iter().flat_map(|coord| [coord.lat(), coord.lng()]));
        },
    )
}
