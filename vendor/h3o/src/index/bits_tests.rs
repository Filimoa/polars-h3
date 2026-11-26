use super::*;
use crate::{CellIndex, Resolution};

#[test]
fn first_axe_none() {
    let index =
        CellIndex::try_from(0x8f2800000000000).expect("valid cell index");
    let result = first_axe(index.into());
    assert_eq!(result, None, "zero til the end");

    let index =
        CellIndex::try_from(0x8029fffffffffff).expect("valid cell index");
    let result = first_axe(index.into());
    assert_eq!(result, None, "no cell");

    let index =
        CellIndex::try_from(0x832800fffffffff).expect("valid cell index");
    let result = first_axe(index.into());
    assert_eq!(result, None, "some zero then unused");
}

#[test]
fn first_axe_some() {
    let resolutions = Resolution::range(Resolution::One, Resolution::Fifteen);
    let indexes = [
        0x8f287478ab9c2ab, // 20-1-6-4-3-6-1-2-5-6-3-4-1-2-5-3
        0x8f283478ab9c2ab, // 20-0-6-4-3-6-1-2-5-6-3-4-1-2-5-3
        0x8f280478ab9c2ab, // 20-0-0-4-3-6-1-2-5-6-3-4-1-2-5-3
        0x8f280078ab9c2ab, // 20-0-0-0-3-6-1-2-5-6-3-4-1-2-5-3
        0x8f280018ab9c2ab, // 20-0-0-0-0-6-1-2-5-6-3-4-1-2-5-3
        0x8f280000ab9c2ab, // 20-0-0-0-0-0-1-2-5-6-3-4-1-2-5-3
        0x8f2800002b9c2ab, // 20-0-0-0-0-0-0-2-5-6-3-4-1-2-5-3
        0x8f2800000b9c2ab, // 20-0-0-0-0-0-0-0-5-6-3-4-1-2-5-3
        0x8f280000019c2ab, // 20-0-0-0-0-0-0-0-0-6-3-4-1-2-5-3
        0x8f280000001c2ab, // 20-0-0-0-0-0-0-0-0-0-3-4-1-2-5-3
        0x8f28000000042ab, // 20-0-0-0-0-0-0-0-0-0-0-4-1-2-5-3
        0x8f28000000002ab, // 20-0-0-0-0-0-0-0-0-0-0-0-1-2-5-3
        0x8f28000000000ab, // 20-0-0-0-0-0-0-0-0-0-0-0-0-2-5-3
        0x8f280000000002b, // 20-0-0-0-0-0-0-0-0-0-0-0-0-0-5-3
        0x8f2800000000003, // 20-0-0-0-0-0-0-0-0-0-0-0-0-0-0-3
    ];

    for (resolution, value) in resolutions.zip(indexes) {
        let index = CellIndex::try_from(value).expect("valid cells");
        let expected = index.direction_at(resolution).and_then(Direction::axe);

        let result = first_axe(index.into());

        assert_eq!(result, expected, "resolution {resolution:?}");
    }
}

// Keep the scalar implementation as an independent oracle for the packed
// rotation, including header bits, center digits and unused suffix digits.
fn scalar_rotate<const CCW: bool>(mut bits: u64, count: usize) -> u64 {
    for resolution in Resolution::range(Resolution::One, get_resolution(bits)) {
        let direction =
            Direction::new_unchecked(get_direction(bits, resolution));
        bits = set_direction(
            bits,
            direction.rotate60::<CCW>(count).into(),
            resolution,
        );
    }
    bits
}

#[test]
fn packed_rotations_match_scalar() {
    let mut state = 0x7a91_9d36_b052_e4c1_u64;
    for resolution in Resolution::range(Resolution::Zero, Resolution::Fifteen) {
        for _ in 0..4096 {
            let mut bits = set_resolution(0x08f2_9fff_ffff_ffff, resolution);
            for level in Resolution::range(Resolution::One, resolution) {
                state ^= state << 13;
                state ^= state >> 7;
                state ^= state << 17;
                let digit = u8::try_from(state % 7).expect("direction");
                bits = set_direction(bits, digit, level);
            }
            for count in 0..12 {
                assert_eq!(
                    rotate60::<true>(bits, count),
                    scalar_rotate::<true>(bits, count)
                );
                assert_eq!(
                    rotate60::<false>(bits, count),
                    scalar_rotate::<false>(bits, count)
                );
            }
        }
    }
}

#[test]
fn packed_rotations_preserve_centers_and_unused_digits() {
    for resolution in Resolution::range(Resolution::Zero, Resolution::Fifteen) {
        let mut bits = set_resolution(0x0802_9fff_ffff_ffff, resolution);
        for level in Resolution::range(Resolution::One, resolution) {
            bits = set_direction(bits, 0, level);
        }
        for count in 0..6 {
            assert_eq!(rotate60::<true>(bits, count), bits);
            assert_eq!(rotate60::<false>(bits, count), bits);
        }
    }
}
