//! IJK Coordinates
//!
//! Discrete hexagon planar grid systems naturally have 3 coordinate axes spaced
//! 120° apart. We refer to such a system as an `IJK` coordinate system, for the
//! three coordinate axes `i`, `j`, and `k`.
//!
//! Using an `IJK` coordinate system to address hexagon grid cells provides
//! multiple valid addresses for each cell. Normalizing an `IJK` address creates
//! a unique address consisting of the minimal positive `IJK` components; this
//! always results in at most two non-zero components.

use super::{CoordCube, SQRT3_2, Vec2d};
use crate::{Direction, error::HexGridError, math::mul_add};
use core::{
    cmp, fmt,
    ops::{Add, MulAssign, Sub},
};

// An integer divided by seven cannot land on a half-integer. Its distance
// from a rounding boundary is at least 1/14, far above the floating-point
// error of the previous f64 multiply for any i32 numerator. Widen before
// adding the rounding offset so i32::MIN/MAX remain valid inputs.
#[inline]
#[expect(clippy::cast_possible_truncation, reason = "quotient fits in i32")]
fn round_seventh(value: i32) -> i32 {
    let value = i64::from(value);
    ((value + if value < 0 { -3 } else { 3 }) / 7) as i32
}

// -----------------------------------------------------------------------------

/// IJ hexagon coordinates.
///
/// Each axis is spaced 120 degrees apart.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash, Ord, PartialOrd)]
#[cfg_attr(feature = "serde", derive(serde::Serialize, serde::Deserialize))]
pub struct CoordIJ {
    /// `i` component.
    pub i: i32,
    /// `j` component.
    pub j: i32,
}

impl CoordIJ {
    /// Initializes a new `IJ` coordinate with the specified component values.
    #[must_use]
    pub const fn new(i: i32, j: i32) -> Self {
        Self { i, j }
    }
}

impl TryFrom<CoordIJ> for CoordIJK {
    type Error = HexGridError;

    // Returns the `IJK` coordinates corresponding to the `IJ` one.
    #[inline]
    fn try_from(value: CoordIJ) -> Result<Self, Self::Error> {
        Self::new(value.i, value.j, 0)
            .checked_normalize()
            .ok_or_else(|| HexGridError::new("IJ coordinates overflow"))
    }
}

impl fmt::Display for CoordIJ {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "({}, {})", self.i, self.j)
    }
}

// -----------------------------------------------------------------------------

/// IJK hexagon coordinates.
///
/// Each axis is spaced 120 degrees apart.
#[derive(Debug, Clone, Default, Copy, Eq, PartialEq)]
pub struct CoordIJK {
    /// `i` component.
    i: i32,
    /// `j` component.
    j: i32,
    /// `k` component.
    k: i32,
}

impl CoordIJK {
    /// Initializes a new IJK coordinate with the specified component values.
    #[inline]
    pub const fn new(i: i32, j: i32, k: i32) -> Self {
        Self { i, j, k }
    }

    /// Returns the `i` component.
    pub const fn i(&self) -> i32 {
        self.i
    }

    /// Returns the `j` component.
    pub const fn j(&self) -> i32 {
        self.j
    }

    /// Returns the `k` component.
    pub const fn k(&self) -> i32 {
        self.k
    }

    /// Normalizes by setting the components to the smallest possible values.
    #[inline]
    pub fn normalize(mut self) -> Self {
        let min = cmp::min(self.i, cmp::min(self.j, self.k));

        self.i -= min;
        self.j -= min;
        self.k -= min;

        self
    }

    /// Normalizes by setting the components to the smallest possible values.
    ///
    /// Guard against overflow (to be used when input comes from user).
    #[inline]
    fn checked_normalize(mut self) -> Option<Self> {
        let min = cmp::min(self.i, cmp::min(self.j, self.k));

        self.i = self.i.checked_sub(min)?;
        self.j = self.j.checked_sub(min)?;
        self.k = self.k.checked_sub(min)?;

        Some(self)
    }

    #[inline]
    pub fn distance(&self, other: &Self) -> i32 {
        let diff = (*self - *other).normalize();

        cmp::max(diff.i.abs(), cmp::max(diff.j.abs(), diff.k.abs()))
    }

    /// Returns the normalized `IJK` coordinates of the indexing parent of a
    /// cell in an aperture 7 grid.
    #[inline]
    pub fn up_aperture7<const CCW: bool>(&self) -> Self {
        let CoordIJ { i, j } = self.into();

        let (i, j) = if CCW {
            (3 * i - j, i + 2 * j)
        } else {
            (2 * i + j, 3 * j - i)
        };

        Self::new(round_seventh(i), round_seventh(j), 0).normalize()
    }

    /// Returns the normalized `IJK` coordinates of the indexing parent of a
    /// cell in an aperture 7 grid.
    #[inline]
    pub fn checked_up_aperture7<const CCW: bool>(&self) -> Option<Self> {
        let CoordIJ { i, j } = self.into();

        let (i, j) = if CCW {
            (
                i.checked_mul(3)?.checked_sub(j)?,
                j.checked_mul(2)?.checked_add(i)?,
            )
        } else {
            (
                i.checked_mul(2)?.checked_add(j)?,
                j.checked_mul(3)?.checked_sub(i)?,
            )
        };

        Self::new(round_seventh(i), round_seventh(j), 0).checked_normalize()
    }

    /// Returns the normalized `IJK` coordinates of the hex centered on the
    /// indicated hex at the next finer aperture 7 resolution.
    #[inline]
    pub fn down_aperture7<const CCW: bool>(&self) -> Self {
        // Resolution `r` unit vectors in resolution `r+1`.
        let (mut i_vec, mut j_vec, mut k_vec) = if CCW {
            (Self::new(3, 0, 1), Self::new(1, 3, 0), Self::new(0, 1, 3))
        } else {
            (Self::new(3, 1, 0), Self::new(0, 3, 1), Self::new(1, 0, 3))
        };

        i_vec *= self.i;
        j_vec *= self.j;
        k_vec *= self.k;

        (i_vec + j_vec + k_vec).normalize()
    }

    /// Applies a Class III then Class II refinement and their two digits.
    /// The opposite aperture-seven rotations compose to a scale of seven,
    /// modulo a common IJK translation removed by normalization.
    #[inline]
    pub fn down_aperture49(&self, digits: u8) -> Self {
        let offset = APERTURE49_OFFSETS[usize::from(digits)];
        Self::new(
            7 * self.i + offset.i,
            7 * self.j + offset.j,
            7 * self.k + offset.k,
        )
        .normalize()
    }

    /// Returns the normalized `IJK` coordinates of the hex centered on the
    /// indicated hex at the next finer aperture 3 resolution.
    #[inline]
    pub fn down_aperture3<const CCW: bool>(&self) -> Self {
        // Resolution `r` unit vectors in resolution `r+1`.
        let (mut i_vec, mut j_vec, mut k_vec) = if CCW {
            (Self::new(2, 0, 1), Self::new(1, 2, 0), Self::new(0, 1, 2))
        } else {
            (Self::new(2, 1, 0), Self::new(0, 2, 1), Self::new(1, 0, 2))
        };

        i_vec *= self.i;
        j_vec *= self.j;
        k_vec *= self.k;

        (i_vec + j_vec + k_vec).normalize()
    }

    /// Returns the normalized `IJK` coordinates of the hex in the specified
    /// direction from the current position.
    #[inline]
    pub fn neighbor(&self, direction: Direction) -> Self {
        (*self + direction.coordinate()).normalize()
    }

    /// Returns the `IJK` coordinates after a 60 degrees rotation.
    #[inline]
    pub fn rotate60<const CCW: bool>(&self) -> Self {
        // Unit vector rotations.
        let (mut i_vec, mut j_vec, mut k_vec) = if CCW {
            (Self::new(1, 1, 0), Self::new(0, 1, 1), Self::new(1, 0, 1))
        } else {
            (Self::new(1, 0, 1), Self::new(1, 1, 0), Self::new(0, 1, 1))
        };
        i_vec *= self.i;
        j_vec *= self.j;
        k_vec *= self.k;

        (i_vec + j_vec + k_vec).normalize()
    }
}

// -----------------------------------------------------------------------------

impl Add for CoordIJK {
    type Output = Self;

    fn add(self, other: Self) -> Self {
        Self {
            i: self.i + other.i,
            j: self.j + other.j,
            k: self.k + other.k,
        }
    }
}

impl Sub for CoordIJK {
    type Output = Self;

    fn sub(self, other: Self) -> Self {
        Self {
            i: self.i - other.i,
            j: self.j - other.j,
            k: self.k - other.k,
        }
    }
}

impl MulAssign<i32> for CoordIJK {
    fn mul_assign(&mut self, rhs: i32) {
        self.i *= rhs;
        self.j *= rhs;
        self.k *= rhs;
    }
}

// -----------------------------------------------------------------------------

impl From<CoordIJK> for Vec2d {
    // Returns the center point in 2D cartesian coordinates of a hex.
    #[inline]
    fn from(value: CoordIJK) -> Self {
        let i = f64::from(value.i - value.k);
        let j = f64::from(value.j - value.k);

        Self::new(mul_add(0.5, -j, i), j * SQRT3_2)
    }
}

impl From<&CoordIJK> for CoordIJ {
    // Returns the `IJ` coordinate corresponding to the the `IJK` one.
    #[inline]
    fn from(value: &CoordIJK) -> Self {
        Self::new(value.i - value.k, value.j - value.k)
    }
}

impl From<CoordIJK> for CoordCube {
    #[inline]
    fn from(value: CoordIJK) -> Self {
        let i = -value.i + value.k;
        let j = value.j - value.k;
        let k = -i - j;

        Self::new(i, j, k)
    }
}

impl TryFrom<CoordIJK> for Direction {
    type Error = HexGridError;

    // Returns the direction corresponding to a given unit vector in `IJK`
    // coordinates.
    #[inline]
    fn try_from(value: CoordIJK) -> Result<Self, Self::Error> {
        let value = value.normalize();

        // First, make sure we have a unit vector in `ijk`.
        if (value.i | value.j | value.k) & !1 == 0 {
            #[expect(
                clippy::cast_possible_truncation,
                clippy::cast_sign_loss,
                reason = "cannot truncate thx to check above (unit vector)"
            )]
            let bits = ((value.i << 2) | (value.j << 1) | value.k) as u8;

            // SAFETY: thx to `normalize` we are guaranteed to have at most two
            // non-zero components, hence max value is 6 (thus valid).
            Ok(Self::new_unchecked(bits))
        } else {
            Err(HexGridError::new("non-unit vector in IJK coordinate"))
        }
    }
}

#[cfg(test)]
#[path = "./ijk_tests.rs"]
mod tests;

// The upper digit is applied before the lower digit. Transform its unit
// vector clockwise, then add the lower digit's vector.
const APERTURE49_OFFSETS: [CoordIJK; 64] = aperture49_offsets();

const fn aperture49_offsets() -> [CoordIJK; 64] {
    const DIGITS: [CoordIJK; 8] = [
        CoordIJK::new(0, 0, 0),
        CoordIJK::new(0, 0, 1),
        CoordIJK::new(0, 1, 0),
        CoordIJK::new(0, 1, 1),
        CoordIJK::new(1, 0, 0),
        CoordIJK::new(1, 0, 1),
        CoordIJK::new(1, 1, 0),
        CoordIJK::new(1, 1, 1),
    ];
    let mut result = [CoordIJK::new(0, 0, 0); 64];
    let mut digits = 0;
    while digits < 64 {
        let first = DIGITS[digits >> 3];
        let second = DIGITS[digits & 7];
        result[digits] = CoordIJK::new(
            3 * first.i + first.k + second.i,
            first.i + 3 * first.j + second.j,
            first.j + 3 * first.k + second.k,
        );
        digits += 1;
    }
    result
}
