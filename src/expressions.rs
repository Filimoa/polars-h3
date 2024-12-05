#![allow(clippy::unused_unit)]
use h3o::{LatLng, Resolution};
use polars::prelude::*;
use pyo3_polars::derive::polars_expr;

#[polars_expr(output_type=UInt64)]
fn latlng_to_cell(inputs: &[Series]) -> PolarsResult<Series> {
    crate::engine::core::latlng_to_cell(&inputs)
}

// #[polars_expr(output_type=String)]
// fn latlng_to_cell_string(inputs: &[Series]) -> PolarsResult<Series> {
//     let resolution = inputs[2].u8()?;
//     let resolution = resolution.get(0).unwrap_or(9);
//     crate::engine::core::latlng_to_cell_string(&inputs[..2], resolution)
// }
