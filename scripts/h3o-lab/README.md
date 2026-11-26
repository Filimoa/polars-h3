# h3o differential laboratory

This standalone Rust workspace compares the local `vendor/h3o` path dependency
with the pinned crates.io **h3o 0.11.0**. Both implementations run in the same
process with the same inputs. Its separate lockfile keeps development-only
reference and benchmark dependencies out of the Python extension.

From the repository root:

    make test-h3o-lab
    H3O_LAB_POINTS=1000000 make test-h3o-lab
    make bench-h3o-lab
    make fuzz-h3o-lab FUZZ_SECONDS=300

The tests cover global deterministic coordinates at every resolution, all cells
through resolution 2, and all pentagons and their nearby cells at every
resolution. They compare integer IDs, list order, boundary/center floating-point
bits, area, vertices, directed-edge destinations, disks and rings. Fallible fast
iterators stop on the first failure as required by their API contract.
Additional checks cover boundary coordinates and their adjacent floating-point
values, malformed cell IDs and validation errors, and ordered polygon coverage
with holes, antimeridian crossings and all four containment modes.

The fuzz target also tries arbitrary finite coordinates outside normal geographic
ranges and valid raw cell IDs. It compares against the original Rust library,
so inherited Rust/C differences do not hide newly introduced regressions. Keep
running `make test-h3o` and the upstream C-reference fuzz targets as independent
checks; known disagreements are documented in `vendor/h3o/UPSTREAM.md`.
`make fuzz-h3o-lab` first seeds the corpus with all-resolution global coordinates,
pentagon boundaries and adjacent floats, base-cell centers, and extreme inputs.
It preserves an existing corpus. Run the `seed-corpus` binary with an optional
destination directory to inspect or reproduce those inputs independently.

Criterion benchmarks use 1,024 varied inputs per iteration. They distinguish
global and Ohio distributions and indexing resolutions 0, 5, 9 and 15. A disk
benchmark measures the radius-3 fast iterator at resolutions 0, 1, 5, 9 and 15.
Boundary, center-coordinate, validation, edge and vertex benchmarks cover
resolution 9. Polygon benchmarks cover Paris at resolutions 9 and 11 and Rabi at
resolution 9, excluding the setup clone. Run without competing builds or tests,
repeat promising results, then verify them through the Python benchmark
suite. These are targeted microbenchmarks, not evidence for unmeasured APIs or
all geographic workloads.

For short exploratory timings:

    cargo bench --manifest-path scripts/h3o-lab/Cargo.toml --bench core -- --warm-up-time 0.2 --measurement-time 0.5

Fuzzing requires nightly Rust and cargo-fuzz, as documented in the vendored
provenance file. Corpus, crash artifacts and build results remain local/ignored.
