#![no_main]
use libfuzzer_sys::fuzz_target;

fuzz_target!(|data: [u64; 3]| {
    let resolution = (data[2] & 15) as u8;
    if let Some(bits) = h3o_lab::assert_coordinate_equivalent(
        f64::from_bits(data[0]),
        f64::from_bits(data[1]),
        resolution,
    ) {
        h3o_lab::assert_cell_equivalent(bits, true);
        // Keep generated sets bounded while exercising complete and partial
        // subtrees, pentagons, duplicates and heterogeneous-resolution errors.
        if data[2] & 16 != 0 {
            let cell = h3o_reference::CellIndex::try_from(bits).unwrap();
            let target = h3o_reference::Resolution::try_from((resolution + 2).min(15)).unwrap();
            let mut cells = cell.children(target).map(u64::from).collect::<Vec<_>>();
            h3o_lab::assert_compaction_equivalent(&cells);
            cells.retain(|value| value.wrapping_mul(data[0]) & 4 == 0);
            h3o_lab::assert_compaction_equivalent(&cells);
            cells.extend([bits, bits]);
            h3o_lab::assert_compaction_equivalent(&cells);
        }
    }
    if h3o_lab::assert_index_validation_equivalent(data[2]) {
        h3o_lab::assert_cell_equivalent(data[2], true);
    }
});
