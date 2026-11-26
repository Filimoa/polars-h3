use criterion::{BenchmarkId, Criterion, criterion_group, criterion_main};
use std::hint::black_box;

fn core(c: &mut Criterion) {
    for ohio in [false, true] {
        let region = if ohio { "ohio" } else { "global" };
        let points = h3o_lab::coordinates(1024, ohio);
        for resolution in [0_u8, 5, 9, 15] {
            let mut group = c.benchmark_group(format!("index/{region}"));
            group.sample_size(30);
            macro_rules! bench_index {
                ($library:ident, $name:literal) => {{
                    let points = points
                        .iter()
                        .map(|&(lat, lng)| $library::LatLng::new(lat, lng).unwrap())
                        .collect::<Vec<_>>();
                    let res = $library::Resolution::try_from(resolution).unwrap();
                    group.bench_function(BenchmarkId::new($name, resolution), |b| {
                        b.iter(|| {
                            for point in &points {
                                black_box(black_box(*point).to_cell(res));
                            }
                        })
                    });
                }};
            }
            bench_index!(h3o_reference, "reference");
            bench_index!(h3o, "candidate");
            group.finish();
        }
        for resolution in [0_u8, 1, 5, 9, 15] {
            let mut group = c.benchmark_group(format!("disk/{region}"));
            group.sample_size(30);
            macro_rules! bench_disk {
                ($library:ident, $name:literal) => {{
                    let cells = points
                        .iter()
                        .map(|&(lat, lng)| {
                            $library::LatLng::new(lat, lng)
                                .unwrap()
                                .to_cell($library::Resolution::try_from(resolution).unwrap())
                        })
                        .collect::<Vec<_>>();
                    group.bench_function(BenchmarkId::new($name, resolution), |b| {
                        b.iter(|| {
                            for cell in &cells {
                                for entry in black_box(*cell).grid_disk_fast(3) {
                                    if black_box(entry).is_none() {
                                        break;
                                    }
                                }
                            }
                        })
                    });
                }};
            }
            bench_disk!(h3o_reference, "reference");
            bench_disk!(h3o, "candidate");
            group.finish();
        }
        let mut group = c.benchmark_group(format!("validate/{region}"));
        group.sample_size(30);
        let valid = points
            .iter()
            .map(|&(lat, lng)| {
                u64::from(
                    h3o_reference::LatLng::new(lat, lng)
                        .unwrap()
                        .to_cell(h3o_reference::Resolution::Nine),
                )
            })
            .collect::<Vec<_>>();
        group.bench_function("reference", |b| {
            b.iter(|| {
                for &bits in &valid {
                    black_box(h3o_reference::CellIndex::try_from(black_box(bits))).ok();
                }
            })
        });
        group.bench_function("candidate", |b| {
            b.iter(|| {
                for &bits in &valid {
                    black_box(h3o::CellIndex::try_from(black_box(bits))).ok();
                }
            })
        });
        group.finish();
        let mut group = c.benchmark_group(format!("edge/{region}"));
        group.sample_size(30);
        macro_rules! bench_edges {
            ($library:ident, $name:literal) => {{
                let pairs = points
                    .iter()
                    .flat_map(|&(lat, lng)| {
                        let cell = $library::LatLng::new(lat, lng)
                            .unwrap()
                            .to_cell($library::Resolution::Nine);
                        cell.edges().map(move |edge| (cell, edge.destination()))
                    })
                    .collect::<Vec<_>>();
                group.bench_function($name, |b| {
                    b.iter(|| {
                        for &(origin, destination) in &pairs {
                            black_box(black_box(origin).edge(black_box(destination)));
                        }
                    })
                });
            }};
        }
        bench_edges!(h3o_reference, "reference");
        bench_edges!(h3o, "candidate");
        group.finish();
        macro_rules! bench_cells {
            ($operation:literal, $library:ident, $name:literal, $calculate:expr) => {{
                let cells = points
                    .iter()
                    .map(|&(lat, lng)| {
                        $library::LatLng::new(lat, lng)
                            .unwrap()
                            .to_cell($library::Resolution::Nine)
                    })
                    .collect::<Vec<_>>();
                let mut group = c.benchmark_group(format!("{}/{region}", $operation));
                group.sample_size(30);
                group.bench_function($name, |b| {
                    b.iter(|| {
                        for &cell in &cells {
                            black_box(($calculate)(black_box(cell)));
                        }
                    })
                });
                group.finish();
            }};
        }
        bench_cells!(
            "vertex",
            h3o_reference,
            "reference",
            |cell: h3o_reference::CellIndex| cell
                .vertex(h3o_reference::Vertex::try_from(0).unwrap())
        );
        bench_cells!("vertex", h3o, "candidate", |cell: h3o::CellIndex| cell
            .vertex(h3o::Vertex::try_from(0).unwrap()));
        bench_cells!(
            "vertexes",
            h3o_reference,
            "reference",
            |cell: h3o_reference::CellIndex| {
                for vertex in cell.vertexes() {
                    black_box(vertex);
                }
            }
        );
        bench_cells!("vertexes", h3o, "candidate", |cell: h3o::CellIndex| {
            for vertex in cell.vertexes() {
                black_box(vertex);
            }
        });
        bench_cells!(
            "boundary",
            h3o_reference,
            "reference",
            |cell: h3o_reference::CellIndex| cell.boundary()
        );
        bench_cells!("boundary", h3o, "candidate", |cell: h3o::CellIndex| cell
            .boundary());
        bench_cells!(
            "center",
            h3o_reference,
            "reference",
            h3o_reference::LatLng::from
        );
        bench_cells!("center", h3o, "candidate", h3o::LatLng::from);
        bench_cells!(
            "area",
            h3o_reference,
            "reference",
            |cell: h3o_reference::CellIndex| cell.area_rads2()
        );
        bench_cells!("area", h3o, "candidate", |cell: h3o::CellIndex| cell
            .area_rads2());
    }
}
fn polygons(c: &mut Criterion) {
    for (name, resolution) in [("Paris", 9_u8), ("Paris", 11), ("Rabi", 9)] {
        let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
            .join(format!("../../vendor/h3o/dataset/shapes/{name}.geojson"));
        let json = geojson::GeoJson::from_reader(std::fs::File::open(path).unwrap()).unwrap();
        let polygon = geo::Polygon::try_from(geo::Geometry::try_from(json).unwrap()).unwrap();
        let mut group = c.benchmark_group(format!("polygon/{name}/{resolution}"));
        group.sample_size(30);
        macro_rules! bench_polygon {
            ($library:ident, $label:literal) => {{
                let mut tiler = $library::geom::TilerBuilder::new(
                    $library::Resolution::try_from(resolution).unwrap(),
                )
                .build();
                tiler.add(polygon.clone()).unwrap();
                group.bench_function($label, |b| {
                    b.iter_batched(
                        || tiler.clone(),
                        |tiler| {
                            for entry in black_box(tiler).into_annotated_coverage() {
                                black_box(entry);
                            }
                        },
                        criterion::BatchSize::PerIteration,
                    )
                });
            }};
        }
        bench_polygon!(h3o_reference, "reference");
        bench_polygon!(h3o, "candidate");
        group.finish();
    }
}
fn compaction(c: &mut Criterion) {
    for workload in ["subtree", "disk", "scattered"] {
        let mut group = c.benchmark_group(format!("compact/{workload}"));
        group.sample_size(30);
        macro_rules! bench_compact {
            ($library:ident, $label:literal) => {{
                let center = $library::LatLng::new(40., -82.).unwrap();
                let cells = match workload {
                    "subtree" => center
                        .to_cell($library::Resolution::Five)
                        .children($library::Resolution::Nine)
                        .collect::<Vec<_>>(),
                    "disk" => center
                        .to_cell($library::Resolution::Nine)
                        .grid_disk::<Vec<_>>(30),
                    _ => h3o_lab::coordinates(32, false)
                        .into_iter()
                        .flat_map(|(lat, lng)| {
                            $library::LatLng::new(lat, lng)
                                .unwrap()
                                .to_cell($library::Resolution::Seven)
                                .children($library::Resolution::Nine)
                        })
                        .collect::<Vec<_>>(),
                };
                group.bench_function($label, |b| {
                    b.iter_batched(
                        || cells.clone(),
                        |mut cells| {
                            $library::CellIndex::compact(&mut cells).unwrap();
                            black_box(cells)
                        },
                        criterion::BatchSize::SmallInput,
                    )
                });
            }};
        }
        bench_compact!(h3o_reference, "reference");
        bench_compact!(h3o, "candidate");
        group.finish();
    }
}
criterion_group!(benches, core, polygons, compaction);
criterion_main!(benches);
