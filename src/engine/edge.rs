use h3o::DirectedEdgeIndex;
use polars::prelude::*;
use rayon::prelude::*;

use super::utils::{map_cell_lists, map_cell_pairs, map_indices};

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

fn parse_edge_indices(edge_series: &Series) -> PolarsResult<Vec<Option<DirectedEdgeIndex>>> {
    Ok(match edge_series.dtype() {
        DataType::UInt64 => edge_series
            .u64()?
            .iter()
            .map(|opt| opt.and_then(|v| DirectedEdgeIndex::try_from(v).ok()))
            .collect(),
        DataType::Int64 => edge_series
            .i64()?
            .iter()
            .map(|opt| opt.and_then(|v| DirectedEdgeIndex::try_from(v as u64).ok()))
            .collect(),
        DataType::String => edge_series
            .str()?
            .iter()
            .map(|opt| {
                opt.and_then(|s| u64::from_str_radix(s, 16).ok())
                    .and_then(|v| DirectedEdgeIndex::try_from(v).ok())
            })
            .collect(),
        _ => {
            return Err(PolarsError::ComputeError(
                format!("Unsupported type for edge: {:?}", edge_series.dtype()).into(),
            ))
        },
    })
}

pub fn is_valid_directed_edge(edge_series: &Series) -> PolarsResult<Series> {
    let is_valid: BooleanChunked = match edge_series.dtype() {
        DataType::UInt64 => edge_series
            .u64()?
            .iter()
            .map(|opt| {
                opt.map(|v| DirectedEdgeIndex::try_from(v).is_ok())
                    .unwrap_or(false)
            })
            .collect(),
        DataType::Int64 => edge_series
            .i64()?
            .iter()
            .map(|opt| {
                opt.map(|v| DirectedEdgeIndex::try_from(v as u64).is_ok())
                    .unwrap_or(false)
            })
            .collect(),
        DataType::String => edge_series
            .str()?
            .iter()
            .map(|opt| {
                opt.and_then(|s| u64::from_str_radix(s, 16).ok())
                    .map(|v| DirectedEdgeIndex::try_from(v).is_ok())
                    .unwrap_or(false)
            })
            .collect(),
        _ => {
            return Err(PolarsError::ComputeError(
                format!("Unsupported type for edge: {:?}", edge_series.dtype()).into(),
            ))
        },
    };

    Ok(is_valid.into_series())
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
    let edges = parse_edge_indices(edge_series)?;

    let cell_pairs: Vec<Option<[u64; 2]>> = edges
        .into_par_iter()
        .map(|edge| edge.map(|idx| [u64::from(idx.origin()), u64::from(idx.destination())]))
        .collect();

    let mut builder = ListPrimitiveChunkedBuilder::<UInt64Type>::new(
        PlSmallStr::from(""),
        cell_pairs.len(),
        cell_pairs.len() * 2,
        DataType::UInt64,
    );
    for opt_pair in cell_pairs {
        match opt_pair {
            Some(pair) => builder.append_slice(&pair),
            None => builder.append_null(),
        }
    }

    Ok(builder.finish().into_series())
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
    let edges = parse_edge_indices(edge_series)?;

    let boundaries: Vec<Option<Vec<f64>>> = edges
        .into_par_iter()
        .map(|edge| {
            edge.map(|idx| {
                let boundary = idx.boundary();
                let mut coords = Vec::with_capacity(boundary.len() * 2);
                for latlng in boundary.iter() {
                    coords.push(latlng.lat());
                    coords.push(latlng.lng());
                }
                coords
            })
        })
        .collect();

    let values_capacity = boundaries
        .iter()
        .filter_map(|opt| opt.as_ref().map(Vec::len))
        .sum();
    let mut builder = ListPrimitiveChunkedBuilder::<Float64Type>::new(
        PlSmallStr::from(""),
        boundaries.len(),
        values_capacity,
        DataType::Float64,
    );
    for opt_boundary in boundaries {
        match opt_boundary {
            Some(boundary) => builder.append_slice(&boundary),
            None => builder.append_null(),
        }
    }

    Ok(builder.finish().into_series())
}
