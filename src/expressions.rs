#![allow(clippy::unused_unit)]
use h3o::{LatLng, Resolution};
use polars::prelude::*;
use pyo3_polars::derive::polars_expr;

#[polars_expr(output_type=UInt64)]
fn lat_lng_to_h3(inputs: &[Series]) -> PolarsResult<Series> {
    crate::core::core::lat_lng_to_h3(inputs)
}
