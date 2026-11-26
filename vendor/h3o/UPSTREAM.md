# Vendored h3o

This is h3o **0.11.0** from <https://github.com/HydroniumLabs/h3o>, revision
`fa1557fd1edd56f64e4da95b2fd294609ce2353e`, imported on 2026-11-25.
The revision is recorded in the published crate's `.cargo_vcs_info.json`; the
initially imported `src/` matched that crate byte for byte. Local optimizations
are listed below. The original BSD-3-Clause
license is in `LICENSE`. Retain it with redistributed source and binaries.

## Local changes

The initial import had no algorithm changes. `UPSTREAM.md` documents provenance;
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

## Core optimization work

The local fork changes these internal paths:

- Rotate packed index digits in parallel using integer bit operations.
- Advance two neighbor digits per lookup, inline ordinary base-cell moves,
  specialize resolution-zero neighbors, and invert the finest digit transition
  to find the sole possible direction for ordinary same-base neighbor pairs.
- Replace integer-valued aperture-seven floating rounding with exact widened
  integer arithmetic; combine pairs of coordinate refinements into one step.
- Cache the twenty face tangent bases under `std`. Coordinate indexing uses
  direct gnomonic projection away from face-center singularities and hexagon
  boundaries, retaining the original angle-based path within conservative
  guards. `no_std` retains the original projection path.
- Validate cell headers and active digits without shifting the whole digit
  field; preserve error precedence for invalid inputs.
- Reuse origin orientation while determining incident vertex directions and
  enumerating all vertices, retaining the center-child shortcut. All-vertex
  iteration also caches neighboring cells and their owner orientations;
  single-vertex calls omit those caches through compile-time specialization.
- Skip compaction ancestors that cannot start at the current sorted cell,
  using its suffix of center digits to identify eligible complete subtrees.
- Stream polygon interior generations without cloning each generation, and
  deduplicate candidates before checking the previous generation's set.

Public signatures, iterator order, invalid-input semantics and floating-point
outputs are preserved. No blanket fast-math or platform-specific CPU flags are
enabled. Performance candidates must pass the pristine Rust-reference
laboratory as well as the preserved upstream suite before acceptance; measured
results and their exact binary provenance are maintained in the parent
project's benchmark reports. Progress reports may describe an earlier saved
binary than the current source; do not combine gains from different snapshots.

The parent `scripts/h3o-lab` workspace pins crates.io h3o 0.11.0 as an independent
reference. Run `make test-h3o-lab`, `make bench-h3o-lab`, and
`make fuzz-h3o-lab FUZZ_SECONDS=300` from the repository root. It checks exact
IDs, iterator order and floating-point bits, including global coordinates,
boundary-adjacent inputs, low-resolution exhaustive cells and pentagon regions.
This complements upstream's C-reference checks without changing their tolerances.

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
outputs remain ignored. Upstream formatting uses nightly rustfmt; install it
with `rustup toolchain install nightly --profile minimal --component rustfmt`.
Run `make lint-h3o` to check vendor and differential-laboratory formatting,
Clippy, the no_std build and vendor benchmarks. Root `make check` includes
these checks; `make fmt` formats the extension and Python separately.

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

A later smoke run found the same class of extreme-coordinate disagreement at
latitude `4.7936642175998674e-304`, longitude `-8.370139123404232e298` radians,
resolution zero. Both pristine h3o and the optimized fork return
`807dfffffffffff`; C H3 returns `8067fffffffffff`. The differential laboratory
preserves this input and compares all sixteen resolutions. This is not a newly
introduced Rust regression, and the C-reference assertion remains enabled.
