//! Differential checks against the immutable crates.io release.

/// Deterministic global coordinates, with a separate ordinary Ohio workload.
pub fn coordinates(count: usize, ohio: bool) -> Vec<(f64, f64)> {
    let mut state = 0x42ac_9b06_1d3e_7f85_u64;
    let mut next = || {
        state ^= state << 13;
        state ^= state >> 7;
        state ^= state << 17;
        (state >> 11) as f64 / ((1_u64 << 53) as f64)
    };
    (0..count)
        .map(|_| {
            if ohio {
                (39.0 + next() * 2.0, -84.0 + next() * 2.0)
            } else {
                (-90.0 + next() * 180.0, -180.0 + next() * 360.0)
            }
        })
        .collect()
}

/// Compare both cell validity and error precedence; return whether it is valid.
pub fn assert_index_validation_equivalent(bits: u64) -> bool {
    let actual = h3o::CellIndex::try_from(bits)
        .map(u64::from)
        .map_err(|err| err.to_string());
    let expected = h3o_reference::CellIndex::try_from(bits)
        .map(u64::from)
        .map_err(|err| err.to_string());
    assert_eq!(actual, expected, "{bits:016x}");
    actual.is_ok()
}

/// Compare compaction results, order and mutations on error.
pub fn assert_compaction_equivalent(bits: &[u64]) {
    let mut actual = bits
        .iter()
        .map(|&bits| h3o::CellIndex::try_from(bits).unwrap())
        .collect::<Vec<_>>();
    let mut expected = bits
        .iter()
        .map(|&bits| h3o_reference::CellIndex::try_from(bits).unwrap())
        .collect::<Vec<_>>();
    assert_eq!(
        h3o::CellIndex::compact(&mut actual).map_err(|err| err.to_string()),
        h3o_reference::CellIndex::compact(&mut expected).map_err(|err| err.to_string())
    );
    // Error paths also mutate the input (sorting/deduplication).
    assert_eq!(
        actual.into_iter().map(u64::from).collect::<Vec<_>>(),
        expected.into_iter().map(u64::from).collect::<Vec<_>>()
    );
}

/// Compare exact values and iterator order with the pinned upstream release.
/// Panics on a regression; intended for tests and fuzzing, not production use.
pub fn assert_cell_equivalent(bits: u64, traversal: bool) {
    let a = h3o::CellIndex::try_from(bits).unwrap();
    let b = h3o_reference::CellIndex::try_from(bits).unwrap();
    let ll_a = h3o::LatLng::from(a);
    let ll_b = h3o_reference::LatLng::from(b);
    assert_eq!(ll_a.lat_radians().to_bits(), ll_b.lat_radians().to_bits());
    assert_eq!(ll_a.lng_radians().to_bits(), ll_b.lng_radians().to_bits());
    assert_eq!(a.area_rads2().to_bits(), b.area_rads2().to_bits());
    let boundary_a = a
        .boundary()
        .iter()
        .map(|ll| (ll.lat_radians().to_bits(), ll.lng_radians().to_bits()))
        .collect::<Vec<_>>();
    let boundary_b = b
        .boundary()
        .iter()
        .map(|ll| (ll.lat_radians().to_bits(), ll.lng_radians().to_bits()))
        .collect::<Vec<_>>();
    assert_eq!(boundary_a, boundary_b);
    assert_eq!(
        a.vertexes().map(u64::from).collect::<Vec<_>>(),
        b.vertexes().map(u64::from).collect::<Vec<_>>()
    );
    for vertex in 0..6 {
        assert_eq!(
            a.vertex(h3o::Vertex::try_from(vertex).unwrap())
                .map(u64::from),
            b.vertex(h3o_reference::Vertex::try_from(vertex).unwrap())
                .map(u64::from)
        );
    }
    assert_eq!(
        a.edges().map(u64::from).collect::<Vec<_>>(),
        b.edges().map(u64::from).collect::<Vec<_>>()
    );
    for (edge_a, edge_b) in a.edges().zip(b.edges()) {
        assert_eq!(
            a.edge(edge_a.destination()).map(u64::from),
            b.edge(edge_b.destination()).map(u64::from)
        );
        assert_eq!(
            u64::from(edge_a.destination()),
            u64::from(edge_b.destination())
        );
    }
    if traversal {
        for k in 0..=3 {
            assert_eq!(
                a.grid_disk::<Vec<_>>(k)
                    .into_iter()
                    .map(u64::from)
                    .collect::<Vec<_>>(),
                b.grid_disk::<Vec<_>>(k)
                    .into_iter()
                    .map(u64::from)
                    .collect::<Vec<_>>()
            );
            assert_eq!(
                a.grid_ring_fast(k)
                    .map(|c| c.map(u64::from))
                    .collect::<Option<Vec<_>>>(),
                b.grid_ring_fast(k)
                    .map(|c| c.map(u64::from))
                    .collect::<Option<Vec<_>>>()
            );
        }
    }
}

/// Compare coordinate indexing, including finite inputs outside normal ranges.
pub fn assert_coordinate_equivalent(lat: f64, lng: f64, resolution: u8) -> Option<u64> {
    let a = h3o::LatLng::from_radians(lat, lng);
    let b = h3o_reference::LatLng::from_radians(lat, lng);
    assert_eq!(a.is_ok(), b.is_ok());
    let (Ok(a), Ok(b)) = (a, b) else { return None };
    let a = a.to_cell(h3o::Resolution::try_from(resolution).unwrap());
    let b = b.to_cell(h3o_reference::Resolution::try_from(resolution).unwrap());
    assert_eq!(
        u64::from(a),
        u64::from(b),
        "{lat},{lng}, resolution {resolution}"
    );
    Some(a.into())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn extreme_coordinates_preserve_pristine_behavior() {
        // Upstream's C-reference fuzzer finds disagreements at extreme finite
        // coordinates. Preserve the pristine Rust results, without relaxing
        // that independent fuzzer or treating C disagreements as regressions.
        for (lat, lng) in [
            (-2.5075187058168033e284, -2.1655354220911844e207),
            (4.7936642175998674e-304, -8.370139123404232e298),
            (f64::MAX, -f64::MAX),
        ] {
            for resolution in 0..=15 {
                assert_coordinate_equivalent(lat, lng, resolution).unwrap();
            }
        }
        assert_eq!(
            assert_coordinate_equivalent(4.7936642175998674e-304, -8.370139123404232e298, 0),
            Some(0x0807_dfff_ffff_ffff)
        );
    }

    #[test]
    fn global_coordinates_and_topology() {
        let count = std::env::var("H3O_LAB_POINTS")
            .map(|value| value.parse().expect("H3O_LAB_POINTS is a positive integer"))
            .unwrap_or(20_000);
        let mut points = coordinates(count, false);
        points.extend([
            (-90.0, -180.0),
            (90.0, 180.0),
            (0.0, 0.0),
            (0.0, 180.0),
            (0.0, -180.0),
        ]);
        for resolution in 0..=15 {
            for (i, &(lat, lng)) in points.iter().enumerate() {
                let a = h3o::LatLng::new(lat, lng)
                    .unwrap()
                    .to_cell(h3o::Resolution::try_from(resolution).unwrap());
                let b = h3o_reference::LatLng::new(lat, lng)
                    .unwrap()
                    .to_cell(h3o_reference::Resolution::try_from(resolution).unwrap());
                assert_eq!(u64::from(a), u64::from(b), "{lat},{lng} res {resolution}");
                if i < 1024 {
                    assert_cell_equivalent(a.into(), i < 256);
                }
            }
        }
    }

    fn assert_polygon_equivalent(polygon: &geo::Polygon, resolution: u8, name: &str) {
        for mode in 0..4 {
            macro_rules! coverage {
                ($library:ident) => {{
                    use $library::geom::{ContainmentMode as M, TilerBuilder};
                    let modes = [
                        M::ContainsCentroid,
                        M::ContainsBoundary,
                        M::IntersectsBoundary,
                        M::Covers,
                    ];
                    let mut tiler =
                        TilerBuilder::new($library::Resolution::try_from(resolution).unwrap())
                            .containment_mode(modes[mode])
                            .build();
                    tiler
                        .add(polygon.clone())
                        .map_err(|err| err.to_string())
                        .map(|()| {
                            tiler
                                .into_annotated_coverage()
                                .map(|entry| (u64::from(entry.cell), entry.is_fully_contained))
                                .collect::<Vec<_>>()
                        })
                }};
            }
            assert_eq!(
                coverage!(h3o),
                coverage!(h3o_reference),
                "{name}, resolution {resolution}, mode {mode}"
            );
        }
    }

    #[test]
    fn polygon_coverage_and_annotations_match() {
        use geo::{Geometry, Polygon};
        let shapes: &[(&str, &[u8])] = &[
            ("Paris", &[0, 4, 9, 11]),
            ("Holes", &[0, 2, 4]),
            ("HalfWorld_1", &[0, 2, 4]),
            ("HalfWorld_2", &[0, 2, 4]),
            ("TransmeridianComplex", &[0, 2, 4]),
            ("TransmeridianHole", &[0, 2, 4]),
            ("Rabi", &[0, 4, 9]),
            ("Empty", &[0, 4, 9]),
            ("h3o_issue21", &[0, 4, 6]),
            ("h3o_issue23", &[0, 2, 4]),
        ];
        for &(name, resolutions) in shapes {
            let path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                .join(format!("../../vendor/h3o/dataset/shapes/{name}.geojson"));
            let json = geojson::GeoJson::from_reader(std::fs::File::open(path).unwrap()).unwrap();
            let polygon = Polygon::try_from(Geometry::try_from(json).unwrap()).unwrap();
            for &resolution in resolutions {
                assert_polygon_equivalent(&polygon, resolution, name);
            }
        }
    }

    #[test]
    fn varied_polygons_and_holes_at_every_resolution() {
        for resolution in 0_u8..=15 {
            let span = (50.0 / 7_f64.powf(f64::from(resolution) / 2.)).min(15.);
            for (index, (lat, lng)) in coordinates(64, false).into_iter().enumerate() {
                let lat = lat.clamp(-89. + span, 89. - span);
                let ring = |scale: f64| {
                    let width = span * scale;
                    let wrap = |x: f64| (x + 180.).rem_euclid(360.) - 180.;
                    geo::LineString::from(vec![
                        (wrap(lng - width), lat - width),
                        (wrap(lng + width), lat - width),
                        (wrap(lng + width), lat + width),
                        (wrap(lng - width), lat + width),
                        (wrap(lng - width), lat - width),
                    ])
                };
                let holes = if index % 2 == 0 {
                    vec![ring(0.3)]
                } else {
                    vec![]
                };
                let polygon = geo::Polygon::new(ring(1.), holes);
                assert_polygon_equivalent(&polygon, resolution, &format!("generated-{index}"));
            }
        }
    }

    #[test]
    fn compaction_preserves_subtrees_partial_sets_and_errors() {
        assert_compaction_equivalent(&[]);
        for value in 0_u8..=15 {
            let resolution = h3o_reference::Resolution::try_from(value).unwrap();
            let target = h3o_reference::Resolution::try_from((value + 3).min(15)).unwrap();
            let mut parents = resolution.pentagons().collect::<Vec<_>>();
            parents.extend(coordinates(16, false).into_iter().map(|(lat, lng)| {
                h3o_reference::LatLng::new(lat, lng)
                    .unwrap()
                    .to_cell(resolution)
            }));
            for parent in parents {
                let mut cells = parent.children(target).map(u64::from).collect::<Vec<_>>();
                cells.reverse();
                assert_compaction_equivalent(&cells);
                assert_compaction_equivalent(&cells[1..]);
                if cells.len() > 3 {
                    cells.remove(cells.len() / 2);
                    assert_compaction_equivalent(&cells);
                }
                cells.push(cells[0]);
                assert_compaction_equivalent(&cells);
                cells.push(parent.into());
                assert_compaction_equivalent(&cells);
            }
        }
    }

    #[test]
    fn validation_and_error_precedence_match() {
        for resolution in 0..=15 {
            for (lat, lng) in coordinates(256, false) {
                let cell = h3o_reference::LatLng::new(lat, lng)
                    .unwrap()
                    .to_cell(h3o_reference::Resolution::try_from(resolution).unwrap());
                let bits = u64::from(cell);
                assert_index_validation_equivalent(bits);
                for bit in 0..64 {
                    assert_index_validation_equivalent(bits ^ (1_u64 << bit));
                }
            }
        }
        let mut state = 0x4ade_1237_b538_9001_u64;
        for _ in 0..1_000_000 {
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            assert_index_validation_equivalent(state);
        }
    }

    #[test]
    fn edge_search_handles_unrelated_and_different_resolution_cells() {
        let points = coordinates(2048, false);
        for resolution in 0..=15 {
            for pair in points.windows(2) {
                let a = h3o_reference::LatLng::new(pair[0].0, pair[0].1)
                    .unwrap()
                    .to_cell(h3o_reference::Resolution::try_from(resolution).unwrap());
                for other_resolution in [resolution, (resolution + 1) % 16] {
                    let b = h3o_reference::LatLng::new(pair[1].0, pair[1].1)
                        .unwrap()
                        .to_cell(h3o_reference::Resolution::try_from(other_resolution).unwrap());
                    let actual = h3o::CellIndex::try_from(u64::from(a))
                        .unwrap()
                        .edge(h3o::CellIndex::try_from(u64::from(b)).unwrap());
                    assert_eq!(actual.map(u64::from), a.edge(b).map(u64::from));
                }
            }
        }
    }

    #[test]
    fn boundary_coordinates_and_adjacent_floats() {
        for resolution in 0..=15 {
            for (lat, lng) in coordinates(256, false) {
                let cell = h3o_reference::LatLng::new(lat, lng)
                    .unwrap()
                    .to_cell(h3o_reference::Resolution::try_from(resolution).unwrap());
                for vertex in cell.boundary().iter() {
                    let lat = vertex.lat_radians();
                    let lng = vertex.lng_radians();
                    for y in [lat.next_down(), lat, lat.next_up()] {
                        for x in [lng.next_down(), lng, lng.next_up()] {
                            assert_coordinate_equivalent(y, x, resolution);
                        }
                    }
                }
            }
        }
    }

    #[test]
    fn all_low_resolution_cells_and_pentagons() {
        for resolution in 0..=2 {
            for base in h3o_reference::CellIndex::base_cells() {
                for cell in base.children(h3o_reference::Resolution::try_from(resolution).unwrap())
                {
                    assert_cell_equivalent(cell.into(), true);
                }
            }
        }
        for resolution in 0..=15 {
            for pentagon in h3o_reference::Resolution::try_from(resolution)
                .unwrap()
                .pentagons()
            {
                for cell in pentagon.grid_disk::<Vec<_>>(3) {
                    assert_cell_equivalent(cell.into(), true);
                }
            }
        }
    }
}
