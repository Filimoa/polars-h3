//! Seed the differential fuzzer with valid topology and difficult coordinates.
use h3o_reference::{CellIndex, LatLng, Resolution};
use std::{fs::OpenOptions, io::Write, path::PathBuf};

struct Corpus {
    directory: PathBuf,
    count: usize,
}

impl Corpus {
    fn emit(&mut self, lat: f64, lng: f64, third: u64) -> std::io::Result<()> {
        let path = self.directory.join(format!("seed-{:05}", self.count));
        self.count += 1;
        match OpenOptions::new().write(true).create_new(true).open(path) {
            Ok(mut file) => {
                // arbitrary's [u64; 3] decoder consumes little-endian words.
                for word in [lat.to_bits(), lng.to_bits(), third] {
                    file.write_all(&word.to_le_bytes())?;
                }
                Ok(())
            },
            Err(error) if error.kind() == std::io::ErrorKind::AlreadyExists => Ok(()),
            Err(error) => Err(error),
        }
    }

    fn cell(&mut self, cell: CellIndex) -> std::io::Result<()> {
        let center = LatLng::from(cell);
        self.emit(center.lat_radians(), center.lng_radians(), cell.into())?;
        let resolution = u64::from(u8::from(cell.resolution()));
        for vertex in cell.boundary().iter() {
            let lat = vertex.lat_radians();
            let lng = vertex.lng_radians();
            for latitude in [lat.next_down(), lat, lat.next_up()] {
                for longitude in [lng.next_down(), lng, lng.next_up()] {
                    self.emit(latitude, longitude, resolution)?;
                }
            }
        }
        Ok(())
    }
}

fn main() -> std::io::Result<()> {
    let directory = std::env::args_os().nth(1).map_or_else(
        || PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("fuzz/corpus/differential"),
        PathBuf::from,
    );
    std::fs::create_dir_all(&directory)?;
    let mut corpus = Corpus {
        directory,
        count: 0,
    };
    for value in 0_u8..=15 {
        let resolution = Resolution::try_from(value).expect("valid resolution");
        for (lat, lng) in h3o_lab::coordinates(32, false) {
            corpus.emit(lat.to_radians(), lng.to_radians(), u64::from(value))?;
        }
        // Both polar and nonpolar pentagons, including their distorted edges.
        for cell in resolution.pentagons() {
            corpus.cell(cell)?;
        }
        // Base-cell centers exercise projection singularities at every scale.
        for cell in CellIndex::base_cells() {
            let center = LatLng::from(cell);
            corpus.emit(center.lat_radians(), center.lng_radians(), u64::from(value))?;
        }
        for lat in [
            0.,
            f64::MIN_POSITIVE,
            1e-300,
            1e100,
            f64::MAX,
            f64::INFINITY,
            f64::NAN,
        ] {
            for lng in [0., std::f64::consts::PI, -std::f64::consts::PI, 1e100] {
                corpus.emit(lat, lng, u64::from(value))?;
                corpus.emit(-lat, -lng, u64::from(value))?;
            }
        }
    }
    println!(
        "Ensured {} seeds in {}",
        corpus.count,
        corpus.directory.display()
    );
    Ok(())
}
