//! Hex2d Coordinates
//!
//! A `Hex2d` coordinate system is a cartesian coordinate system associated with
//! a specific `ijk` coordinate system, where:
//!
//! - the origin of the `Hex2d` system is centered on the origin cell of the
//!   `ijk` system,
//! - the positive `x`-axis of the `Hex2d` system is aligned with the `i`-axis
//!   of the `ijk` system, and
//! - 1.0 unit distance in the `Hex2d` system is the distance between adjacent
//!   cell centers in the `ijk` coordinate system.

use super::{
    AP7_ROT_RADS, CoordIJK, EPSILON, INV_RES0_U_GNOMONIC, SQRT7_POWERS, Vec3d,
};
use crate::{
    Face, Resolution, face,
    math::{abs, acos, mul_add, sin_cos, sqrt, tan},
};
use float_eq::float_eq;

/// 1/sin(60')
const RSIN60: f64 = 1.1547005383792515;

// -----------------------------------------------------------------------------

/// 2D floating-point vector.
#[derive(Debug, Clone, Copy)]
pub struct Vec2d {
    /// `x` component.
    pub x: f64,
    /// `y` component.
    pub y: f64,
}

impl PartialEq for Vec2d {
    fn eq(&self, other: &Self) -> bool {
        float_eq!(self.x, other.x, abs <= f64::from(f32::EPSILON))
            && float_eq!(self.y, other.y, abs <= f64::from(f32::EPSILON))
    }
}

impl Eq for Vec2d {}

impl Vec2d {
    /// Initializes a new 2D vector with the specified component values.
    pub const fn new(x: f64, y: f64) -> Self {
        Self { x, y }
    }

    /// Encodes n-vector to the corresponding icosahedral 2D hex coordinates
    /// relative to the given face center.
    ///
    ///
    /// # Preconditions
    ///
    /// `value` is expected to be on the unit sphere.
    ///
    /// # Arguments
    ///
    /// * `value` - The n-vector to encode.
    /// * `resolution` -  The desired H3 resolution for the encoding.
    /// * `face` -  The icosahedral face of the coordinate.
    /// * `distance` - The squared euclidean distance from the face center.
    pub fn from_vec3d(
        value: Vec3d,
        resolution: Resolution,
        face: Face,
        distance: f64,
    ) -> Self {
        float_eq::debug_assert_float_eq!(value.norm(), 1., abs <= f64::EPSILON);

        let face = usize::from(face);

        let r = {
            // cos(r) = 1 - 2 * sin^2(r/2) = 1 - 2 * (sqd / 4) = 1 - sqd/2
            let r = acos(mul_add(distance, -0.5, 1.));

            if r < EPSILON {
                return Self::new(0., 0.);
            }

            // Perform gnomonic scaling of `r` (`tan(r)`) and scale for current
            // resolution length `u`.
            (tan(r) * INV_RES0_U_GNOMONIC)
                * SQRT7_POWERS[usize::from(resolution)]
        };

        let theta = {
            // Compute counter-clockwise `theta` from Class II i-axis.
            let mut theta = face::AXES_AZ_RADS_CII[face]
                - Vec3d::face_azimuth(face, &value);

            // Adjust `theta` for Class III.
            if resolution.is_class3() {
                theta -= AP7_ROT_RADS;
            }
            theta
        };

        // Convert to local x, y.
        let (sin_t, cos_t) = sin_cos(theta);
        Self::new(r * cos_t, r * sin_t)
    }

    /// Quantize a gnomonic projection, preserving the original calculation
    /// near face centers and cell edges where floating-point rounding matters.
    pub fn to_coord_ijk(
        value: Vec3d,
        resolution: Resolution,
        face: Face,
        distance: f64,
    ) -> CoordIJK {
        #[cfg(feature = "std")]
        if distance >= 1e-10 {
            // Project directly onto the face tangent plane. This is the same
            // gnomonic geometry as tan(acos(...)) plus azimuth/sin/cos, without
            // the intermediate angles. Keep a generous guard around every
            // quantization edge and use the original arithmetic there.
            static AXES: std::sync::LazyLock<
                [[(f64, f64); 2]; crate::NUM_ICOSA_FACES],
            > = std::sync::LazyLock::new(|| {
                core::array::from_fn(|i| {
                    [
                        sin_cos(face::AXES_AZ_RADS_CII[i]),
                        sin_cos(face::AXES_AZ_RADS_CII[i] - AP7_ROT_RADS),
                    ]
                })
            });
            let f = usize::from(face);
            let (north, east) = Vec3d::face_tangent_basis(f);
            let (sin_axis, cos_axis) =
                AXES[f][usize::from(resolution.is_class3())];
            let n = value.dot(&north);
            let e = value.dot(&east);
            let scale =
                INV_RES0_U_GNOMONIC * SQRT7_POWERS[usize::from(resolution)];
            let radial = scale / value.dot(&face::CENTER_POINT[f]);
            let projected = Self::new(
                mul_add(cos_axis, n, sin_axis * e) * radial,
                mul_add(sin_axis, n, -cos_axis * e) * radial,
            );
            let coord = CoordIJK::from(projected);
            let center = Self::from(coord);
            let dx = projected.x - center.x;
            let dy = projected.y - center.y;
            // The three neighbor bisectors bound the convex hexagonal cell.
            // The original angle path is ill-conditioned right at a face
            // center (excluded above); elsewhere a 1e-9 angular guard is far
            // larger than the accumulated double-precision rounding error.
            // Two coordinate errors project to at most twice this guard.
            let guard = 2.0e-9 * scale;
            let limit = 0.5 - guard;
            if abs(dx) < limit
                && abs(mul_add(-0.5, dx, super::SQRT3_2 * dy)) < limit
                && abs(mul_add(-0.5, dx, -super::SQRT3_2 * dy)) < limit
            {
                return coord;
            }
        }
        Self::from_vec3d(value, resolution, face, distance).into()
    }

    /// Calculates the magnitude.
    pub fn magnitude(self) -> f64 {
        sqrt(mul_add(self.x, self.x, self.y * self.y))
    }

    /// Finds the intersection between two lines.
    ///
    /// Assumes that the lines intersect and that the intersection is not at an
    /// endpoint of either line.
    pub fn intersection(line1: (Self, Self), line2: (Self, Self)) -> Self {
        let s1 = Self {
            x: line1.1.x - line1.0.x,
            y: line1.1.y - line1.0.y,
        };
        let s2 = Self {
            x: line2.1.x - line2.0.x,
            y: line2.1.y - line2.0.y,
        };

        let t = mul_add(
            s2.x,
            line1.0.y - line2.0.y,
            -s2.y * (line1.0.x - line2.0.x),
        ) / mul_add(-s2.x, s1.y, s1.x * s2.y);

        Self {
            x: mul_add(t, s1.x, line1.0.x),
            y: mul_add(t, s1.y, line1.0.y),
        }
    }
}

impl From<Vec2d> for CoordIJK {
    // Returns the containing hex in `IJK` coordinates for a 2D cartesian
    // coordinate vector (from DGGRID).
    #[inline]
    fn from(value: Vec2d) -> Self {
        // Quantize into the IJ system and then normalize.
        let k = 0;

        let a1 = abs(value.x);
        let a2 = abs(value.y);

        // First do a reverse conversion.
        let x2 = a2 * RSIN60;
        let x1 = a1 + x2 / 2.;

        // Check if we have the center of a hex.
        #[expect(clippy::cast_possible_truncation, reason = "on purpose")]
        let m1 = x1 as i32;
        #[expect(clippy::cast_possible_truncation, reason = "on purpose")]
        let m2 = x2 as i32;

        // Otherwise round correctly.
        let r1 = x1 - f64::from(m1);
        let r2 = x2 - f64::from(m2);

        let (mut i, mut j) = if r1 < 0.5 {
            if r1 < 1. / 3. {
                let i = m1;
                let j = m2 + i32::from(r2 >= f64::midpoint(1., r1));
                (i, j)
            } else {
                let i = m1 + i32::from((1. - r1) <= r2 && r2 < (2. * r1));
                let j = m2 + i32::from(r2 >= (1. - r1));
                (i, j)
            }
        } else if r1 < 2. / 3. {
            let j = m2 + i32::from(r2 >= (1. - r1));
            let i =
                m1 + i32::from(mul_add(2.0, r1, -1.) >= r2 || r2 >= (1. - r1));
            (i, j)
        } else {
            let i = m1 + 1;
            let j = m2 + i32::from(r2 >= (r1 / 2.));
            (i, j)
        };

        // Now fold across the axes if necessary.
        if value.x < 0. {
            let offset = j % 2;
            let axis_i = i32::midpoint(j, offset);
            let diff = i - axis_i;
            i -= 2 * diff + offset;
        }

        if value.y < 0. {
            i -= (2 * j + 1) / 2;
            j = -j;
        }

        Self::new(i, j, k).normalize()
    }
}

#[cfg(test)]
#[path = "./vec2d_tests.rs"]
mod tests;
