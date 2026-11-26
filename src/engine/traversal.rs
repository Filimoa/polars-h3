use h3o::{CellIndex, CoordIJ};
use polars::prelude::*;

use super::utils::{
    cast_list_u64_to_dtype, for_each_index, map_cell_pairs, parallel_chunks,
    parallel_chunks_with_min, parse_cell_indices, resolve_target_inner_dtype,
};

pub fn grid_distance(origin_series: &Series, destination_series: &Series) -> PolarsResult<Series> {
    map_cell_pairs::<Int32Type, _, _>(origin_series, destination_series, |origin, dest| {
        match (origin, dest) {
            (Some(org), Some(dst)) => org.grid_distance(dst).ok(),
            _ => None,
        }
    })
}

pub fn grid_ring(inputs: &[Series]) -> PolarsResult<Series> {
    grid_lists(inputs, false)
}

pub fn grid_disk(inputs: &[Series]) -> PolarsResult<Series> {
    grid_lists(inputs, true)
}

fn grid_lists(inputs: &[Series], disk: bool) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    let k_series = &inputs[1];
    // Check the input type before radius errors, without parsing the full column.
    parse_cell_indices(&cell_series.slice(0, 0))?;
    let target_dtype = resolve_target_inner_dtype(cell_series.dtype())?;
    let k_cast = k_series.cast(&DataType::Int32)?;
    let radii = k_cast.i32()?;
    let scalar = k_series.len() == 1 && !matches!(k_series.dtype(), DataType::List(_));
    let scalar_k = if scalar {
        let k = radii.get(0).ok_or_else(|| {
            PolarsError::ComputeError(
                (if disk {
                    "k_series is empty"
                } else {
                    "k_series is empty or invalid"
                })
                .into(),
            )
        })?;
        if !disk && k < 0 {
            polars_bail!(ComputeError: "k must be non-negative");
        }
        Some(k)
    } else {
        if radii.len() != cell_series.len() {
            if disk {
                polars_bail!(ComputeError: "k_series length ({}) must match cell_series length ({})", radii.len(), cell_series.len());
            }
            polars_bail!(ComputeError: "Length of k_series ({}) must match cell_series ({})", radii.len(), cell_series.len());
        }
        None
    };

    // Reserve for common scalar radii without speculative huge allocations for
    // large radii or invalid/null inputs. Variable-radius batches grow normally.
    let values_per_cell = scalar_k.filter(|&k| k >= 0).map_or(7, |k| {
        let k = k as u64;
        let size = if disk {
            1 + 3 * k * (k + 1)
        } else {
            (6 * k).max(1)
        };
        size.min(128) as usize
    });
    let out = parallel_chunks(cell_series.len(), |offset, len| {
        let cells = cell_series.slice(offset as i64, len);
        let batch_radii = radii.slice(offset as i64, if scalar { 0 } else { len });
        let mut builder = ListPrimitiveChunkedBuilder::<UInt64Type>::new(
            PlSmallStr::EMPTY,
            len,
            len * values_per_cell,
            DataType::UInt64,
        );
        // Reuse disk scratch across rows. A failed fast traversal must discard
        // its entire partial result before using the safe pentagon traversal.
        let mut scratch = Vec::new();
        let mut position = 0;
        for_each_index::<CellIndex, _>(&cells, "h3 cell", |cell| {
            let radius = scalar_k.or_else(|| batch_radii.get(position));
            position += 1;
            match (cell, radius) {
                (Some(cell), Some(radius)) if radius >= 0 => {
                    let radius = radius as u32;
                    if disk {
                        scratch.clear();
                        let complete = cell
                            .grid_disk_fast(radius)
                            .try_for_each(|cell| cell.map(|cell| scratch.push(u64::from(cell))))
                            .is_some();
                        if !complete {
                            scratch.clear();
                            scratch.extend(cell.grid_disk_safe(radius).map(u64::from));
                        }
                        builder.append_slice(&scratch);
                    } else {
                        // Preserve the existing fast-ring API's pentagon behavior.
                        builder.append_values_iter(
                            cell.grid_ring_fast(radius).flatten().map(u64::from),
                        );
                    }
                },
                _ => builder.append_null(),
            }
        })?;
        Ok(builder.finish().into_series())
    })?;
    match &target_dtype {
        DataType::UInt64 => Ok(out),
        DataType::Int64 => out.cast(&DataType::List(Box::new(DataType::Int64))),
        _ => cast_list_u64_to_dtype(&out, &DataType::UInt64, Some(&target_dtype)),
    }
}

pub fn grid_path_cells(
    origin_series: &Series,
    destination_series: &Series,
) -> PolarsResult<Series> {
    let dtype = resolve_target_inner_dtype(origin_series.dtype())?;
    let output = parallel_chunks_with_min(
        origin_series.len().min(destination_series.len()),
        256,
        |offset, len| {
            let origins = parse_cell_indices(&origin_series.slice(offset as i64, len))?;
            let destinations = parse_cell_indices(&destination_series.slice(offset as i64, len))?;
            let mut builder = ListPrimitiveChunkedBuilder::<UInt64Type>::new(
                PlSmallStr::EMPTY,
                len,
                len * 8,
                DataType::UInt64,
            );
            for (origin, destination) in origins.into_iter().zip(destinations) {
                let path = origin
                    .zip(destination)
                    .and_then(|(org, dst)| org.grid_path_cells(dst).ok());
                match path {
                    Some(path) => {
                        builder.append_values_iter(path.filter_map(Result::ok).map(u64::from))
                    },
                    None => builder.append_null(),
                }
            }
            Ok(builder.finish().into_series())
        },
    )?;
    match dtype {
        DataType::UInt64 => Ok(output),
        DataType::Int64 => output.cast(&DataType::List(Box::new(DataType::Int64))),
        _ => cast_list_u64_to_dtype(&output, &DataType::UInt64, Some(&dtype)),
    }
}

pub fn cell_to_local_ij(cell_series: &Series, origin_series: &Series) -> PolarsResult<Series> {
    parallel_chunks_with_min(
        cell_series.len().min(origin_series.len()),
        1024,
        |offset, len| {
            let cells = parse_cell_indices(&cell_series.slice(offset as i64, len))?;
            let origins = parse_cell_indices(&origin_series.slice(offset as i64, len))?;
            let mut builder = ListPrimitiveChunkedBuilder::<Float64Type>::new(
                PlSmallStr::EMPTY,
                len,
                len * 2,
                DataType::Float64,
            );
            for (cell, origin) in cells.into_iter().zip(origins) {
                match cell
                    .zip(origin)
                    .and_then(|(cell, origin)| cell.to_local_ij(origin).ok())
                {
                    Some(coord) => {
                        builder.append_slice(&[coord.coord.i as f64, coord.coord.j as f64])
                    },
                    None => builder.append_null(),
                }
            }
            Ok(builder.finish().into_series())
        },
    )
}

pub fn local_ij_to_cell(
    origin_series: &Series,
    i_series: &Series,
    j_series: &Series,
) -> PolarsResult<Series> {
    // Validate the H3 dtype before coordinate casts, as in the scalar path.
    parse_cell_indices(&origin_series.slice(0, 0))?;
    let i_coords = i_series.cast(&DataType::Int32)?;
    let j_coords = j_series.cast(&DataType::Int32)?;
    parallel_chunks_with_min(
        origin_series.len().min(i_coords.len()).min(j_coords.len()),
        1024,
        |offset, len| {
            let origins = parse_cell_indices(&origin_series.slice(offset as i64, len))?;
            let i_values = i_coords.slice(offset as i64, len);
            let j_values = j_coords.slice(offset as i64, len);
            let cells: UInt64Chunked = origins
                .into_iter()
                .zip(i_values.i32()?.iter().zip(j_values.i32()?.iter()))
                .map(|(origin, (i, j))| {
                    let local_ij = h3o::LocalIJ::new(origin?, CoordIJ { i: i?, j: j? });
                    CellIndex::try_from(local_ij).ok().map(u64::from)
                })
                .collect();
            Ok(cells.into_series())
        },
    )
}
