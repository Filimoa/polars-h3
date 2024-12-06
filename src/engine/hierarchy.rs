use super::utils::parse_cell_indices;
use h3o::{CellIndex, Resolution};
use polars::prelude::*;
use rayon::prelude::*;

fn get_target_resolution(cell: CellIndex, target_res: Option<u8>) -> Option<Resolution> {
    match target_res {
        Some(res) => Resolution::try_from(res).ok(),
        None => {
            let curr_res = cell.resolution();
            // Get next resolution if None provided
            curr_res.succ()
        },
    }
}

pub fn cell_to_parent(cell_series: &Series, parent_res: Option<u8>) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let parents: UInt64Chunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.and_then(|idx| {
                let target_res = if let Some(res) = parent_res {
                    Resolution::try_from(res).ok()
                } else {
                    idx.resolution().pred()
                };
                target_res.and_then(|res| idx.parent(res))
            })
            .map(Into::into)
        })
        .collect();

    Ok(parents.into_series())
}

pub fn cell_to_center_child(cell_series: &Series, child_res: Option<u8>) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let center_children: UInt64Chunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.and_then(|idx| {
                let target_res = get_target_resolution(idx, child_res)?;
                idx.center_child(target_res)
            })
            .map(Into::into)
        })
        .collect();

    Ok(center_children.into_series())
}

pub fn cell_to_children_size(cell_series: &Series, child_res: Option<u8>) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let sizes: UInt64Chunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.map(|idx| {
                let target_res = get_target_resolution(idx, child_res)
                    .unwrap_or_else(|| idx.resolution().succ().unwrap_or(idx.resolution()));
                idx.children_count(target_res)
            })
        })
        .collect();

    Ok(sizes.into_series())
}

pub fn cell_to_children(cell_series: &Series, child_res: Option<u8>) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let children: ListChunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.map(|idx| {
                let target_res = get_target_resolution(idx, child_res)
                    .unwrap_or_else(|| idx.resolution().succ().unwrap_or(idx.resolution()));
                let children: Vec<u64> = idx.children(target_res).map(Into::into).collect();
                Series::new(PlSmallStr::from(""), children.as_slice())
            })
        })
        .collect();

    Ok(children.into_series())
}

pub fn cell_to_child_pos(child_series: &Series, parent_res: u8) -> PolarsResult<Series> {
    let cells = parse_cell_indices(child_series)?;

    let positions: UInt64Chunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.and_then(|idx| {
                let parent_res = Resolution::try_from(parent_res).ok()?;
                idx.child_position(parent_res)
            })
        })
        .collect();

    Ok(positions.into_series())
}
pub fn child_pos_to_cell(
    parent_series: &Series,
    child_res: u8,
    pos_series: &Series,
) -> PolarsResult<Series> {
    let parents = parse_cell_indices(parent_series)?;
    let positions = pos_series.u64()?;

    // Convert positions to Vec to ensure we can do parallel iteration
    let pos_vec: Vec<Option<u64>> = positions.into_iter().collect();

    let children: UInt64Chunked = parents
        .into_par_iter()
        .zip(pos_vec.into_par_iter())
        .map(|(parent, pos)| match (parent, pos) {
            (Some(parent), Some(pos)) => {
                let child_res = Resolution::try_from(child_res).ok()?;
                parent.child_at(pos, child_res).map(Into::into)
            },
            _ => None,
        })
        .collect();

    Ok(children.into_series())
}
pub fn compact_cells(cell_series: &Series) -> PolarsResult<Series> {
    if let DataType::List(_) = cell_series.dtype() {
        let ca = cell_series.list()?;
        let cells_vec: Vec<_> = ca.into_iter().collect();

        let compacted: ListChunked = cells_vec
            .into_par_iter()
            .map(|opt_series| {
                opt_series
                    .map(|series| {
                        let cells = parse_cell_indices(&series)?;
                        let cell_vec: Vec<_> = cells.into_iter().flatten().collect();

                        CellIndex::compact(cell_vec)
                            .map_err(|e| {
                                PolarsError::ComputeError(format!("Compaction error: {}", e).into())
                            })
                            .map(|compacted| {
                                Series::new(
                                    PlSmallStr::from(""),
                                    compacted.into_iter().map(u64::from).collect::<Vec<_>>(),
                                )
                            })
                    })
                    .transpose()
            })
            .collect::<PolarsResult<_>>()?;

        Ok(compacted.into_series())
    } else {
        let cells = parse_cell_indices(cell_series)?;
        let cell_vec: Vec<_> = cells.into_iter().flatten().collect();

        let compacted = CellIndex::compact(cell_vec)
            .map_err(|e| PolarsError::ComputeError(format!("Compaction error: {}", e).into()))?;

        let compacted_cells: ListChunked = vec![Some(Series::new(
            PlSmallStr::from(""),
            compacted.into_iter().map(u64::from).collect::<Vec<_>>(),
        ))]
        .into_iter()
        .collect();

        Ok(compacted_cells.into_series())
    }
}

pub fn uncompact_cells(cell_series: &Series, res: u8) -> PolarsResult<Series> {
    let target_res = Resolution::try_from(res)
        .map_err(|_| PolarsError::ComputeError("Invalid resolution".into()))?;

    if let DataType::List(_) = cell_series.dtype() {
        let ca = cell_series.list()?;
        let cells_vec: Vec<_> = ca.into_iter().collect();

        let uncompacted: ListChunked = cells_vec
            .into_par_iter()
            .map(|opt_series| {
                opt_series
                    .map(|series| {
                        let cells = parse_cell_indices(&series)?;
                        let cell_vec: Vec<_> = cells.into_iter().flatten().collect();

                        let uncompacted = CellIndex::uncompact(cell_vec, target_res);
                        Ok(Series::new(
                            PlSmallStr::from(""),
                            uncompacted.into_iter().map(u64::from).collect::<Vec<_>>(),
                        ))
                    })
                    .transpose()
            })
            .collect::<PolarsResult<_>>()?;

        Ok(uncompacted.into_series())
    } else {
        let cells = parse_cell_indices(cell_series)?;
        let cell_vec: Vec<_> = cells.into_iter().flatten().collect();
        let uncompacted: ListChunked = vec![Some(Series::new(
            PlSmallStr::from(""),
            CellIndex::uncompact(cell_vec, target_res)
                .map(u64::from)
                .collect::<Vec<_>>(),
        ))]
        .into_iter()
        .collect();

        Ok(uncompacted.into_series())
    }
}
