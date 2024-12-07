use h3o::DirectedEdgeIndex;
use polars::prelude::*;
use rayon::prelude::*;

use super::utils::parse_cell_indices;

pub fn are_neighbor_cells(
    origin_series: &Series,
    destination_series: &Series,
) -> PolarsResult<Series> {
    let origins = parse_cell_indices(origin_series)?;
    let destinations = parse_cell_indices(destination_series)?;

    let dest_vec: Vec<_> = destinations.into_iter().collect();

    let are_neighbors: BooleanChunked = origins
        .into_par_iter()
        .zip(dest_vec.into_par_iter())
        .map(|(origin, dest)| match (origin, dest) {
            (Some(org), Some(dst)) => org.is_neighbor_with(dst).ok().unwrap_or(false),
            _ => false,
        })
        .collect();

    Ok(are_neighbors.into_series())
}

pub fn cells_to_directed_edge(
    origin_series: &Series,
    destination_series: &Series,
) -> PolarsResult<Series> {
    let origins = parse_cell_indices(origin_series)?;
    let destinations = parse_cell_indices(destination_series)?;

    let dest_vec: Vec<_> = destinations.into_iter().collect();

    let edges: UInt64Chunked = origins
        .into_par_iter()
        .zip(dest_vec.into_par_iter())
        .map(|(origin, dest)| match (origin, dest) {
            (Some(org), Some(dst)) => org.edge(dst).map(Into::into),
            _ => None,
        })
        .collect();

    Ok(edges.into_series())
}

fn parse_edge_indices(edge_series: &Series) -> PolarsResult<Vec<Option<DirectedEdgeIndex>>> {
    Ok(match edge_series.dtype() {
        DataType::UInt64 => edge_series
            .u64()?
            .into_iter()
            .map(|opt| opt.and_then(|v| DirectedEdgeIndex::try_from(v).ok()))
            .collect(),
        DataType::Int64 => edge_series
            .i64()?
            .into_iter()
            .map(|opt| opt.and_then(|v| DirectedEdgeIndex::try_from(v as u64).ok()))
            .collect(),
        DataType::String => edge_series
            .str()?
            .into_iter()
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
            .into_iter()
            .map(|opt| {
                opt.map(|v| DirectedEdgeIndex::try_from(v).is_ok())
                    .unwrap_or(false)
            })
            .collect(),
        DataType::Int64 => edge_series
            .i64()?
            .into_iter()
            .map(|opt| {
                opt.map(|v| DirectedEdgeIndex::try_from(v as u64).is_ok())
                    .unwrap_or(false)
            })
            .collect(),
        DataType::String => edge_series
            .str()?
            .into_iter()
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
    let edges = parse_edge_indices(edge_series)?;

    let origins: UInt64Chunked = edges
        .into_par_iter()
        .map(|edge| edge.map(|idx| u64::from(idx.origin())))
        .collect();

    Ok(origins.into_series())
}

pub fn get_directed_edge_destination(edge_series: &Series) -> PolarsResult<Series> {
    let edges = parse_edge_indices(edge_series)?;

    let destinations: UInt64Chunked = edges
        .into_par_iter()
        .map(|edge| edge.map(|idx| u64::from(idx.destination())))
        .collect();

    Ok(destinations.into_series())
}

pub fn directed_edge_to_cells(edge_series: &Series) -> PolarsResult<Series> {
    let edges = parse_edge_indices(edge_series)?;

    let cell_pairs: ListChunked = edges
        .into_par_iter()
        .map(|edge| {
            edge.map(|idx| {
                Series::new(
                    PlSmallStr::from_str(""),
                    &[u64::from(idx.origin()), u64::from(idx.destination())],
                )
            })
        })
        .collect();

    Ok(cell_pairs.into_series())
}

pub fn origin_to_directed_edges(cell_series: &Series) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let edges: ListChunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.map(|idx| {
                let edge_list: Vec<u64> = idx.edges().map(Into::into).collect();
                Series::new(PlSmallStr::from_str(""), edge_list.as_slice())
            })
        })
        .collect();

    Ok(edges.into_series())
}

pub fn directed_edge_to_boundary(edge_series: &Series) -> PolarsResult<Series> {
    let edges = parse_edge_indices(edge_series)?;

    let boundaries: ListChunked = edges
        .into_par_iter()
        .map(|edge| {
            edge.map(|idx| {
                let boundary = idx.boundary();
                let coords: Vec<f64> = boundary
                    .iter()
                    .flat_map(|latlng| vec![latlng.lat(), latlng.lng()])
                    .collect();
                Series::new(PlSmallStr::from_str(""), coords.as_slice())
            })
        })
        .collect();

    Ok(boundaries.into_series())
}
