#![allow(clippy::unused_unit)]
use polars::prelude::*;
use pyo3_polars::derive::polars_expr;
use serde::Deserialize;

#[derive(Deserialize)]
struct LatLngToCellKwargs {
    resolution: u8,
}

#[derive(Deserialize)]
struct ResolutionKwargs {
    resolution: Option<u8>,
}

#[derive(Deserialize)]
struct GridKwargs {
    k: u32,
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

#[polars_expr(output_type=UInt64)]
fn str_to_int(inputs: &[Series]) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    crate::engine::inspection::str_to_int(cell_series)
}

#[polars_expr(output_type=String)]
fn int_to_str(inputs: &[Series]) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    crate::engine::inspection::int_to_str(cell_series)
}

#[polars_expr(output_type=Boolean)]
fn is_valid_cell(inputs: &[Series]) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    crate::engine::inspection::is_valid_cell(cell_series)
}

#[polars_expr(output_type=Boolean)]
fn is_pentagon(inputs: &[Series]) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    crate::engine::inspection::is_pentagon(cell_series)
}

#[polars_expr(output_type=Boolean)]
fn is_res_class_III(inputs: &[Series]) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    crate::engine::inspection::is_res_class_III(cell_series)
}

fn faces_list_dtype(input_fields: &[Field]) -> PolarsResult<Field> {
    let field = Field::new(
        input_fields[0].name.clone(),
        DataType::List(Box::new(DataType::Int64)),
    );
    Ok(field)
}

#[polars_expr(output_type_func=faces_list_dtype)]
fn get_icosahedron_faces(inputs: &[Series]) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    crate::engine::inspection::get_icosahedron_faces(cell_series)
}

fn list_uint64_dtype(input_fields: &[Field]) -> PolarsResult<Field> {
    Ok(Field::new(
        input_fields[0].name.clone(),
        DataType::List(Box::new(DataType::UInt64)),
    ))
}

#[polars_expr(output_type=UInt64)]
fn cell_to_parent(inputs: &[Series], kwargs: ResolutionKwargs) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    crate::engine::hierarchy::cell_to_parent(cell_series, kwargs.resolution)
}

#[polars_expr(output_type=UInt64)]
fn cell_to_center_child(inputs: &[Series], kwargs: ResolutionKwargs) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    crate::engine::hierarchy::cell_to_center_child(cell_series, kwargs.resolution)
}

#[polars_expr(output_type=UInt64)]
fn cell_to_children_size(inputs: &[Series], kwargs: ResolutionKwargs) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    crate::engine::hierarchy::cell_to_children_size(cell_series, kwargs.resolution)
}

#[polars_expr(output_type_func=list_uint64_dtype)]
fn cell_to_children(inputs: &[Series], kwargs: ResolutionKwargs) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    crate::engine::hierarchy::cell_to_children(cell_series, kwargs.resolution)
}

#[polars_expr(output_type=UInt64)]
fn cell_to_child_pos(inputs: &[Series], kwargs: ResolutionKwargs) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    crate::engine::hierarchy::cell_to_child_pos(cell_series, kwargs.resolution.unwrap_or(0))
}

#[polars_expr(output_type=UInt64)]
fn child_pos_to_cell(inputs: &[Series], kwargs: ResolutionKwargs) -> PolarsResult<Series> {
    let parent_series = &inputs[0];
    let pos_series = &inputs[1];
    crate::engine::hierarchy::child_pos_to_cell(
        parent_series,
        kwargs.resolution.unwrap_or(0),
        pos_series,
    )
}

#[polars_expr(output_type_func=list_uint64_dtype)]
fn compact_cells(inputs: &[Series]) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    crate::engine::hierarchy::compact_cells(cell_series)
}

#[polars_expr(output_type_func=list_uint64_dtype)]
fn uncompact_cells(inputs: &[Series], kwargs: ResolutionKwargs) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    let resolution = kwargs.resolution.ok_or_else(|| {
        PolarsError::ComputeError("Resolution required for uncompact_cells".into())
    })?;
    crate::engine::hierarchy::uncompact_cells(cell_series, resolution)
}

#[polars_expr(output_type=Int32)]
fn grid_distance(inputs: &[Series]) -> PolarsResult<Series> {
    let origin_series = &inputs[0];
    let destination_series = &inputs[1];
    crate::engine::traversal::grid_distance(origin_series, destination_series)
}

#[polars_expr(output_type_func=list_uint64_dtype)]
fn grid_ring(inputs: &[Series], kwargs: GridKwargs) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    crate::engine::traversal::grid_ring(cell_series, kwargs.k)
}

#[polars_expr(output_type_func=list_uint64_dtype)]
fn grid_disk(inputs: &[Series], kwargs: GridKwargs) -> PolarsResult<Series> {
    let cell_series = &inputs[0];
    crate::engine::traversal::grid_disk(cell_series, kwargs.k)
}

#[polars_expr(output_type_func=list_uint64_dtype)]
fn grid_path_cells(inputs: &[Series]) -> PolarsResult<Series> {
    let origin_series = &inputs[0];
    let destination_series = &inputs[1];
    crate::engine::traversal::grid_path_cells(origin_series, destination_series)
}
