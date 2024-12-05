use super::utils::parse_cell_indices;
use h3o::CellIndex;
use polars::prelude::*;
use rayon::prelude::*;

pub fn grid_distance(origin_series: &Series, destination_series: &Series) -> PolarsResult<Series> {
    let origins = parse_cell_indices(origin_series)?;
    let destinations = parse_cell_indices(destination_series)?;

    // Convert to Vec to ensure parallel iteration works
    let dest_vec: Vec<_> = destinations.into_iter().collect();

    let distances: Int32Chunked = origins
        .into_par_iter()
        .zip(dest_vec.into_par_iter())
        .map(|(origin, dest)| match (origin, dest) {
            (Some(org), Some(dst)) => org.grid_distance(dst).ok().map(|d| d),
            _ => None,
        })
        .collect();

    Ok(distances.into_series())
}

pub fn grid_ring(cell_series: &Series, k: u32) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;

    let rings: ListChunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.map(|idx| {
                let ring_cells: Vec<u64> = idx
                    .grid_ring_fast(k)
                    .filter_map(|opt_cell| opt_cell.map(Into::into))
                    .collect();
                Series::new(PlSmallStr::from(""), ring_cells.as_slice())
            })
        })
        .collect();

    Ok(rings.into_series())
}

pub fn grid_disk(cell_series: &Series, k: u32) -> PolarsResult<Series> {
    let cells = parse_cell_indices(cell_series)?;
    let disks: ListChunked = cells
        .into_par_iter()
        .map(|cell| {
            cell.map(|idx| {
                let disk_cells: Vec<_> = CellIndex::grid_disks_fast(vec![idx], k)
                    .flatten() // Flatten the Option<CellIndex>
                    .map(Into::<u64>::into) // Convert CellIndex to u64
                    .collect();
                Series::new(PlSmallStr::from(""), disk_cells.as_slice())
            })
        })
        .collect();
    Ok(disks.into_series())
}
pub fn grid_path_cells(
    origin_series: &Series,
    destination_series: &Series,
) -> PolarsResult<Series> {
    let origins = parse_cell_indices(origin_series)?;
    let destinations = parse_cell_indices(destination_series)?;

    // Convert to Vec to ensure parallel iteration works
    let dest_vec: Vec<_> = destinations.into_iter().collect();

    let paths: ListChunked = origins
        .into_par_iter()
        .zip(dest_vec.into_par_iter())
        .map(|(origin, dest)| {
            match (origin, dest) {
                (Some(org), Some(dst)) => {
                    // Collect all cells in the path, handling errors by returning None
                    org.grid_path_cells(dst).ok().map(|path| {
                        let path_cells: Vec<u64> =
                            path.filter_map(Result::ok).map(Into::into).collect();
                        Series::new(PlSmallStr::from(""), path_cells.as_slice())
                    })
                },
                _ => None,
            }
        })
        .collect();

    Ok(paths.into_series())
}