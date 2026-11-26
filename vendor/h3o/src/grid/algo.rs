//! Hexagon grid algorithms.

use crate::{
    BaseCell, CCW, CW, CellIndex, Direction, Resolution, coord::FaceIJK,
    index::bits,
};

// -----------------------------------------------------------------------------

/// Returns the index neighboring the origin, in the specified direction.
///
/// The only case where this returns `None` is when the origin is a pentagon and
/// the translation follow the `K` axe.
///
/// # Arguments
///
/// * `origin`    - Origin index.
/// * `direction` - Direction to move in.
/// * `rotations` - Number of ccw rotations to perform to reorient the
///   translation vector.
///
/// # Returns
///
/// The neighboring index and an updated rotation count (happens when crossing a
/// face edge).
#[inline]
pub fn neighbor_rotations(
    origin: CellIndex,
    direction: Direction,
    rotations: u8,
) -> Option<(CellIndex, u8)> {
    // Center is not a valid direction here.
    debug_assert_ne!(direction, Direction::Center);

    let mut current = u64::from(origin);

    // Adjust the indexing digits and, if needed, the base cell.
    let mut direction = direction.rotate60::<{ CCW }>(rotations.into());
    let mut res = origin.resolution();
    if res == Resolution::Zero {
        return Some(neighbor_base_cell(origin, direction, rotations));
    }
    // Move two resolution digits at a time. Each lookup combines the new
    // digits and the carry into the coarser grid. No carry leaves the other
    // digit unchanged, so the common case completes in one lookup.
    while res >= Resolution::Two {
        let offset = res.direction_offset();
        let digits = ((current >> offset) & 63) as usize;
        let entry = NEIGHBOR_PAIR[usize::from(res.is_class3())]
            [digits * 8 + usize::from(direction)];
        current =
            (current & !(63_u64 << offset)) | (u64::from(entry & 63) << offset);
        #[expect(
            clippy::cast_possible_truncation,
            reason = "table carries are directions 0..=6"
        )]
        let carry = (entry >> 6) as u8;
        direction = Direction::new_unchecked(carry);
        if direction == Direction::Center {
            break;
        }
        res = Resolution::new_unchecked(u8::from(res) - 2);
    }
    if res == Resolution::One {
        let from = usize::from(bits::get_direction(current, res));
        let to = usize::from(direction);
        current = bits::set_direction(
            current,
            NEW_DIRECTION_II[from][to].into(),
            res,
        );
        direction = NEW_ADJUSTMENT_II[from][to];
        if direction != Direction::Center {
            res = Resolution::Zero;
        }
    }

    // Most steps stay inside an ordinary hexagonal base cell. Keep this
    // path small enough to inline into disk/ring iteration; face crossings
    // and pentagon corrections use the unchanged slower path below.
    if res != Resolution::Zero && !origin.base_cell().is_pentagon() {
        return Some((CellIndex::new_unchecked(current), rotations % 6));
    }
    neighbor_rotations_adjusted(origin, current, direction, rotations, res)
}

// At resolution zero there are no direction digits or deleted subsequences
// to rotate. Only the base-cell transition and orientation correction remain.
fn neighbor_base_cell(
    origin: CellIndex,
    mut direction: Direction,
    mut rotations: u8,
) -> (CellIndex, u8) {
    let old = origin.base_cell();
    let new = old.neighbor(direction).unwrap_or_else(|| {
        direction = Direction::IK;
        rotations += 1;
        old.neighbor(direction).expect("pentagon neighbor")
    });
    if old != new
        && new.is_polar_pentagon()
        && u8::from(old) != 118
        && u8::from(old) != 8
    {
        rotations += 1;
    }
    let current = h3o_bit::set_base_cell(origin.into(), new.into());
    (
        CellIndex::new_unchecked(current),
        (rotations + old.neighbor_rotation(direction)) % 6,
    )
}

#[inline(never)]
fn neighbor_rotations_adjusted(
    origin: CellIndex,
    mut current: u64,
    direction: Direction,
    mut rotations: u8,
    res: Resolution,
) -> Option<(CellIndex, u8)> {
    let old_base_cell = origin.base_cell();
    // If `res` is 1, it means we have adjusted indexing digit all the way down.
    // (i.e. no early exit from the loop).
    let new_rotations = if res == Resolution::Zero {
        if let Some(base_cell) = old_base_cell.neighbor(direction) {
            current = h3o_bit::set_base_cell(current, base_cell.into());
            old_base_cell.neighbor_rotation(direction)
        } else {
            // Adjust for the deleted k vertex at the base cell level.
            // This edge actually borders a different neighbor.
            let base_cell = old_base_cell
                .neighbor(Direction::IK)
                .expect("pentagon neighbor");
            current = h3o_bit::set_base_cell(current, base_cell.into());

            // Perform the adjustment for the k-subsequence we're skipping
            // over.
            current = bits::rotate60::<{ CCW }>(current, 1);
            rotations += 1;

            old_base_cell.neighbor_rotation(Direction::IK)
        }
    } else {
        0
    };

    // SAFETY: cell index always contain a valid base cell.
    let new_base_cell =
        BaseCell::new_unchecked(h3o_bit::get_base_cell(current));
    if new_base_cell.is_pentagon() {
        let mut already_adjusted_k_subsequence = false;

        // Force rotation out of missing k-axes sub-sequence.
        if bits::first_axe(current) == Direction::K.axe() {
            if old_base_cell == new_base_cell {
                let old_leading_dir = bits::first_axe(origin.into());

                // In this case, we traversed into the deleted k subsequence
                // from within the same pentagon base cell.
                //
                // Propagate the None because it's undefined: the k direction is
                // deleted from here.
                old_leading_dir?;

                if old_leading_dir == Direction::JK.axe() {
                    // Rotate out of the deleted K subsequence.
                    // We also need an additional change to the direction we're
                    // moving in.
                    current = bits::rotate60::<{ CCW }>(current, 1);
                    rotations += 1;
                } else if old_leading_dir == Direction::IK.axe() {
                    // Rotate out of the deleted K subsequence.
                    // We also need an additional change to the direction we're
                    // moving in.
                    current = bits::rotate60::<{ CW }>(current, 1);
                    rotations += 5;
                }
            } else {
                // In this case, we traversed into the deleted k subsequence of
                // a pentagon base cell.
                // We need to rotate out of that case depending on how we got
                // here.
                // Check for a CW/CCW offset face; default is CCW.

                if new_base_cell.is_cw_offset(FaceIJK::from(old_base_cell).face)
                {
                    current = bits::rotate60::<{ CW }>(current, 1);
                }
                already_adjusted_k_subsequence = true;
            }
        }

        current = (0..new_rotations)
            .fold(current, |acc, _| bits::pentagon_rotate60::<{ CCW }>(acc));

        // Account for differing orientation of the base cells (this edge might
        // not follow properties of some other edges).
        if old_base_cell != new_base_cell {
            let direction = bits::first_axe(current);

            if new_base_cell.is_polar_pentagon() {
                // 'polar' base cells behave differently because they have all
                // `I` neighbors.
                rotations += u8::from(
                    u8::from(old_base_cell) != 118
                        && u8::from(old_base_cell) != 8
                        && direction != Direction::JK.axe(),
                );
            } else {
                // Account for distortion introduced to the 5 neighbor by the
                // deleted `K` subsequence.
                rotations += u8::from(
                    !already_adjusted_k_subsequence
                        && direction == Direction::IK.axe(),
                );
            }
        }
    } else if new_rotations != 0 {
        current = bits::rotate60::<{ CCW }>(current, new_rotations.into());
    }

    Some((
        CellIndex::new_unchecked(current),
        (rotations + new_rotations) % 6,
    ))
}

// -----------------------------------------------------------------------------

/// Finds and returns the direction from the origin to a given neighbor.
///
/// This is effectively the reverse operation for `neighbor_rotations`.
///
/// Returns `None` if the cells are not neighbors.
///
/// Ordinary neighbors within the same base cell use an inverse digit lookup.
/// Base-cell crossings and pentagon cases test the six movement directions.
pub fn direction_for_neighbor(
    origin: CellIndex,
    destination: CellIndex,
) -> Option<Direction> {
    let resolution = origin.resolution();
    if resolution != destination.resolution() || origin == destination {
        return None;
    }
    // Within an ordinary base cell, a neighbor step permutes the finest
    // digit without rotating the index. Invert that permutation to identify
    // the only possible movement, then verify the complete resulting index.
    // Base-cell crossings and pentagon corrections retain the general search.
    let base = origin.base_cell();
    if resolution != Resolution::Zero
        && base == destination.base_cell()
        && !base.is_pentagon()
    {
        let from = usize::from(bits::get_direction(origin.into(), resolution));
        let to =
            usize::from(bits::get_direction(destination.into(), resolution));
        let direction = if resolution.is_class3() {
            INVERSE_DIRECTION_II[from][to]
        } else {
            INVERSE_DIRECTION_III[from][to]
        };
        if direction == Direction::Center {
            return None;
        }
        return (neighbor_rotations(origin, direction, 0).map(|value| value.0)
            == Some(destination))
        .then_some(direction);
    }

    // Skips center since that would be the origin.
    // Skips deleted `K` direction for pentagons.
    let start = 1 + u8::from(origin.is_pentagon());

    // Checks each neighbor, in order, to determine which direction the
    // destination neighbor is located.
    (start..=6).find_map(|value| {
        // SAFETY: loop upper bound is 6 (a.k.a. `Direction::IJ`), which is a
        // valid direction.
        let direction = Direction::new_unchecked(value);
        let neighbor =
            neighbor_rotations(origin, direction, 0).map(|result| result.0);

        (neighbor == Some(destination)).then_some(direction)
    })
}

// -----------------------------------------------------------------------------

// Consts to save some typing below...
const CENTER: Direction = Direction::Center;
const K_AXE: Direction = Direction::K;
const J_AXE: Direction = Direction::J;
const JK_AXE: Direction = Direction::JK;
const I_AXE: Direction = Direction::I;
const IK_AXE: Direction = Direction::IK;
const IJ_AXE: Direction = Direction::IJ;

/// New digit when traversing along class II grids.
///
/// Current digit -> direction -> new digit.
const NEW_DIRECTION_II: [[Direction; 7]; 7] = [
    [CENTER, K_AXE, J_AXE, JK_AXE, I_AXE, IK_AXE, IJ_AXE],
    [K_AXE, I_AXE, JK_AXE, IJ_AXE, IK_AXE, J_AXE, CENTER],
    [J_AXE, JK_AXE, K_AXE, I_AXE, IJ_AXE, CENTER, IK_AXE],
    [JK_AXE, IJ_AXE, I_AXE, IK_AXE, CENTER, K_AXE, J_AXE],
    [I_AXE, IK_AXE, IJ_AXE, CENTER, J_AXE, JK_AXE, K_AXE],
    [IK_AXE, J_AXE, CENTER, K_AXE, JK_AXE, IJ_AXE, I_AXE],
    [IJ_AXE, CENTER, IK_AXE, J_AXE, K_AXE, I_AXE, JK_AXE],
];

/// New traversal direction when traversing along class II grids.
///
/// Current digit -> direction -> new ap7 move (at coarser level).
const NEW_ADJUSTMENT_II: [[Direction; 7]; 7] = [
    [CENTER, CENTER, CENTER, CENTER, CENTER, CENTER, CENTER],
    [CENTER, K_AXE, CENTER, K_AXE, CENTER, IK_AXE, CENTER],
    [CENTER, CENTER, J_AXE, JK_AXE, CENTER, CENTER, J_AXE],
    [CENTER, K_AXE, JK_AXE, JK_AXE, CENTER, CENTER, CENTER],
    [CENTER, CENTER, CENTER, CENTER, I_AXE, I_AXE, IJ_AXE],
    [CENTER, IK_AXE, CENTER, CENTER, I_AXE, IK_AXE, CENTER],
    [CENTER, CENTER, J_AXE, CENTER, IJ_AXE, CENTER, IJ_AXE],
];

/// New traversal direction when traversing along class III grids.
///
/// Current digit -> direction -> new ap7 move (at coarser level).
///
const NEW_DIRECTION_III: [[Direction; 7]; 7] = [
    [CENTER, K_AXE, J_AXE, JK_AXE, I_AXE, IK_AXE, IJ_AXE],
    [K_AXE, J_AXE, JK_AXE, I_AXE, IK_AXE, IJ_AXE, CENTER],
    [J_AXE, JK_AXE, I_AXE, IK_AXE, IJ_AXE, CENTER, K_AXE],
    [JK_AXE, I_AXE, IK_AXE, IJ_AXE, CENTER, K_AXE, J_AXE],
    [I_AXE, IK_AXE, IJ_AXE, CENTER, K_AXE, J_AXE, JK_AXE],
    [IK_AXE, IJ_AXE, CENTER, K_AXE, J_AXE, JK_AXE, I_AXE],
    [IJ_AXE, CENTER, K_AXE, J_AXE, JK_AXE, I_AXE, IK_AXE],
];

/// New traversal direction when traversing along class III grids.
///
/// Current digit -> direction -> new ap7 move (at coarser level).
const NEW_ADJUSTMENT_III: [[Direction; 7]; 7] = [
    [CENTER, CENTER, CENTER, CENTER, CENTER, CENTER, CENTER],
    [CENTER, K_AXE, CENTER, JK_AXE, CENTER, K_AXE, CENTER],
    [CENTER, CENTER, J_AXE, J_AXE, CENTER, CENTER, IJ_AXE],
    [CENTER, JK_AXE, J_AXE, JK_AXE, CENTER, CENTER, CENTER],
    [CENTER, CENTER, CENTER, CENTER, I_AXE, IK_AXE, I_AXE],
    [CENTER, K_AXE, CENTER, CENTER, IK_AXE, IK_AXE, CENTER],
    [CENTER, CENTER, IJ_AXE, CENTER, I_AXE, CENTER, IJ_AXE],
];

// Indexed by finest-resolution parity, two 3-bit digits and movement direction.
// Unused digit/direction 7 entries are unreachable for validated cell indexes.
const NEIGHBOR_PAIR: [[u16; 512]; 2] = neighbor_pairs();

const fn neighbor_pairs() -> [[u16; 512]; 2] {
    let mut result = [[0; 512]; 2];
    let mut parity = 0;
    while parity < 2 {
        let (fine_digits, fine_carries, coarse_digits, coarse_carries) =
            if parity == 1 {
                (
                    NEW_DIRECTION_II,
                    NEW_ADJUSTMENT_II,
                    NEW_DIRECTION_III,
                    NEW_ADJUSTMENT_III,
                )
            } else {
                (
                    NEW_DIRECTION_III,
                    NEW_ADJUSTMENT_III,
                    NEW_DIRECTION_II,
                    NEW_ADJUSTMENT_II,
                )
            };
        let mut high = 0;
        while high < 7 {
            let mut low = 0;
            while low < 7 {
                let mut direction = 0;
                while direction < 7 {
                    let digit = fine_digits[low][direction] as u16;
                    let carry = fine_carries[low][direction] as usize;
                    let upper = coarse_digits[high][carry] as u16;
                    let carry = coarse_carries[high][carry] as u16;
                    result[parity][(high * 8 + low) * 8 + direction] =
                        digit | (upper << 3) | (carry << 6);
                    direction += 1;
                }
                low += 1;
            }
            high += 1;
        }
        parity += 1;
    }
    result
}

const INVERSE_DIRECTION_II: [[Direction; 7]; 7] =
    invert_directions(NEW_DIRECTION_II);
const INVERSE_DIRECTION_III: [[Direction; 7]; 7] =
    invert_directions(NEW_DIRECTION_III);

const fn invert_directions(table: [[Direction; 7]; 7]) -> [[Direction; 7]; 7] {
    let mut result = [[Direction::Center; 7]; 7];
    let mut from = 0;
    while from < 7 {
        let mut direction = 0_u8;
        while direction < 7 {
            let to = table[from][direction as usize] as usize;
            result[from][to] = Direction::new_unchecked(direction);
            direction += 1;
        }
        from += 1;
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn base_cell_steps_match_general_adjustment() {
        for origin in CellIndex::base_cells() {
            for direction in
                Direction::iter().filter(|d| *d != Direction::Center)
            {
                for rotations in 0..6 {
                    let expected = neighbor_rotations_adjusted(
                        origin,
                        origin.into(),
                        direction.rotate60::<{ CCW }>(rotations.into()),
                        rotations,
                        Resolution::Zero,
                    );
                    assert_eq!(
                        neighbor_rotations(origin, direction, rotations),
                        expected
                    );
                }
            }
        }
    }
}
