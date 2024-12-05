#![allow(clippy::unused_unit)]
use h3o::{LatLng, Resolution};
use polars::prelude::*;
use pyo3_polars::derive::polars_expr;
use serde::Deserialize;

#[derive(Deserialize)]
struct LatLngToCellKwargs {
    resolution: u8,
}

#[polars_expr(output_type=UInt64)]
fn latlng_to_cell(inputs: &[Series], kwargs: LatLngToCellKwargs) -> PolarsResult<Series> {
    let lat_series = &inputs[0];
    let lng_series = &inputs[1];
    let resolution = kwargs.resolution;

    crate::engine::core::latlng_to_cell(lat_series, lng_series, resolution)
}

#[polars_expr(output_type = String)]
fn latlng_to_cell_string(inputs: &[Series], kwargs: LatLngToCellKwargs) -> PolarsResult<Series> {
    let lat_series = &inputs[0];
    let lng_series = &inputs[1];
    let resolution = kwargs.resolution;

    crate::engine::core::latlng_to_cell_string(lat_series, lng_series, resolution)
}
