#![allow(clippy::unused_unit)]
use polars::prelude::*;
use pyo3_polars::derive::polars_expr;
use serde::Deserialize;

#[derive(Deserialize)]
struct LatLngToCellKwargs {
    resolution: u8,
}

fn latlng_list_dtype(input_fields: &[Field]) -> PolarsResult<Field> {
    let field = Field::new(
        input_fields[0].name.clone(),
        DataType::List(Box::new(DataType::Float64)),
    );
    Ok(field)
}

#[polars_expr(output_type=UInt64)]
fn latlng_to_cell(inputs: &[Series], kwargs: LatLngToCellKwargs) -> PolarsResult<Series> {
    let lat_series = &inputs[0];
    let lng_series = &inputs[1];
    let resolution = kwargs.resolution;

    crate::engine::indexing::latlng_to_cell(lat_series, lng_series, resolution)
}

#[polars_expr(output_type = String)]
fn latlng_to_cell_string(inputs: &[Series], kwargs: LatLngToCellKwargs) -> PolarsResult<Series> {
    let lat_series = &inputs[0];
    let lng_series = &inputs[1];
    let resolution = kwargs.resolution;

    crate::engine::indexing::latlng_to_cell_string(lat_series, lng_series, resolution)
}

#[polars_expr(output_type=Float64)]
fn cell_to_lat(inputs: &[Series]) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    crate::engine::indexing::cell_to_lat(cell_series)
}

#[polars_expr(output_type=Float64)]
fn cell_to_lng(inputs: &[Series]) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    crate::engine::indexing::cell_to_lng(cell_series)
}

#[polars_expr(output_type_func=latlng_list_dtype)]
fn cell_to_latlng(inputs: &[Series]) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    crate::engine::indexing::cell_to_latlng(cell_series)
}

#[polars_expr(output_type=UInt8)]
fn get_resolution(inputs: &[Series]) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    crate::engine::inspection::get_resolution(cell_series)
}
