# Vendored h3o

This is h3o **0.11.0** from <https://github.com/HydroniumLabs/h3o>, revision
`fa1557fd1edd56f64e4da95b2fd294609ce2353e`, imported on 2026-11-25.
The revision is recorded in the published crate's `.cargo_vcs_info.json`; the
imported `src/` matches that crate byte for byte. The original BSD-3-Clause
license is in `LICENSE`. Retain it with redistributed source and binaries.

## Local changes

No algorithm changes in the initial import. `UPSTREAM.md` documents provenance;
`.gitignore` permits committing dependency lockfiles for tests and fuzzing.
`fuzz/Cargo.toml` explicitly enables `libfuzzer-sys/link_libfuzzer` so the
preserved targets link against the runtime with current libfuzzer-sys releases.
`fuzz/fuzz_targets/cell_index.rs` sorts directed edges before comparing with C
H3, matching the existing upstream integration test: the libraries intentionally
return different edge orders.
The parent project's Cargo.toml uses this directory as a path dependency.
Python packaging includes the fuzz workspace explicitly and ships this crate's
license in wheel metadata. The combined distribution uses the license expression
`MIT AND BSD-3-Clause`; the parent project's own code remains MIT licensed.
Upstream `.github/` files are retained for reference; only workflows at the
root of polars-h3 are active.

## Development and validation

From the polars-h3 root:

    make test-h3o
    make check
    make bench-h3o
    make test-sdist

The standalone crate has its own lockfile. Its tests compare many operations
against C H3 through h3ron-h3-sys and require a C build toolchain. Benchmarks
and tests use the preserved dataset directory. Keep new regression tests near
the corresponding upstream tests. Before accepting performance changes, also
compare results with the pristine upstream revision and measure end-to-end
Polars performance; passing fuzz runs alone does not prove equivalence.

To run a bounded fuzz session, install cargo-fuzz and nightly Rust:

    cargo install cargo-fuzz --version 0.13.2 --locked
    rustup toolchain install nightly --component rust-src
    make fuzz-h3o FUZZ_TARGET=latltng_to_cell FUZZ_SECONDS=60

List targets with `cd vendor/h3o && cargo +nightly fuzz list`. The spelling
`latltng_to_cell` is upstream's target name. The scheduled workflow runs all
targets, caches corpus inputs, and uploads crash artifacts. Minimize failures
and turn them into checked-in regression tests. Fuzz corpus, artifacts and build
outputs remain ignored. Upstream formatting uses nightly rustfmt; run
`cargo +nightly fmt --manifest-path vendor/h3o/Cargo.toml -- --check` when editing
this crate. Root `make fmt` formats the extension separately.

## Updating upstream

Download an exact revision into a temporary directory and review its diff
against this copy. Preserve local patches and regression tests, update this
file's revision and change log, and regenerate the standalone and fuzz
lockfiles intentionally. Run `make check`, compile the benchmarks, and smoke
test the fuzz targets. Build an sdist and a wheel from its extracted contents
before release. Keep upstream synchronization separate from optimizations so
each change is reviewable and can be submitted upstream independently.

## Known baseline fuzz findings

The initial smoke run found a coordinate-conversion disagreement with C H3 at
resolution zero for latitude `-2.5075187058168033e284` and longitude
`-2.1655354220911844e207` radians. These finite but extreme inputs come from
upstream's unrestricted LatLng Arbitrary implementation. The unchanged h3o
source returns `800dfffffffffff`; the C reference returns `8001fffffffffff`.
This finding is unresolved; the scheduled coordinate fuzz job may fail on it.
It is deliberately not filtered out or marked as an allowed CI failure.

The raw input is retained at `fuzz/regressions/latlng_extreme_coordinates.bin`.
Reproduce from this directory with:

    cargo +nightly fuzz run latltng_to_cell fuzz/regressions/latlng_extreme_coordinates.bin

Investigate input-domain and reference-version differences before changing the
algorithm. This initial import makes no claim that all inherited fuzz assertions
pass or that upstream coverage proves equivalence for every input.

After correcting the edge-order comparison, `cell_index` also found a
`cellAreaKm2` tolerance mismatch for cell `8f032020000009b`: h3o returns
`9.567811165919551e-7`, while C H3 returns `9.567812900194557e-7`. The
difference exceeds the harness's existing relative tolerance. Replay with:

    cargo +nightly fuzz run cell_index fuzz/regressions/cell_area_tolerance.bin

The tolerance and algorithms remain unchanged. Fourteen other targets passed
two-second smoke sessions on the import machine; those short runs are not
exhaustive validation. Both findings used the preserved upstream fuzz reference
dependency h3ron-h3-sys 0.16.0; regular upstream tests use 0.17.0.
