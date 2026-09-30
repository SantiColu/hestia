"""Body frame from two body axis → direction pairs (``docs/etapas/environment.md``), vectorized.

The primary body axis points exactly at the primary direction; the secondary axis is as close
as possible to the secondary direction (the TRIAD construction: Shuster & Oh, «Three-axis
attitude determination from vector observations», J. Guidance and Control 4(1), 1981).

Conventions: rotation matrices and quaternions map body → inertial (``v_inertial = C v_body``);
quaternions are ``[w, x, y, z]`` (scalar first), unit and with w ≥ 0.
"""

import numpy as np

from hestia_core.environment.orbit import Axis, Target
from hestia_core.sun import FloatArray

AXIS_VECTORS: dict[Axis, tuple[float, float, float]] = {
    Axis.PX: (1.0, 0.0, 0.0),
    Axis.MX: (-1.0, 0.0, 0.0),
    Axis.PY: (0.0, 1.0, 0.0),
    Axis.MY: (0.0, -1.0, 0.0),
    Axis.PZ: (0.0, 0.0, 1.0),
    Axis.MZ: (0.0, 0.0, -1.0),
}
"""Unit vector of each body axis (and outward normal of each envelope face) in body axes."""

_PARALLEL = 1e-9


def _unit(v: FloatArray) -> FloatArray:
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def target_directions(
    position_m: FloatArray, velocity_m_s: FloatArray, sun_unit: FloatArray
) -> dict[Target, FloatArray]:
    """Inertial unit vector of each target direction, shape (…, 3) each.

    Nadir -r̂, zenith r̂, velocity v̂, orbit normal ĥ = (r x v)/|r x v| and the Sun ŝ.
    """
    r_hat = _unit(position_m)
    v_hat = _unit(velocity_m_s)
    h_hat = _unit(np.cross(position_m, velocity_m_s))
    sun = _unit(np.broadcast_to(sun_unit, r_hat.shape).copy())
    return {
        Target.NADIR: -r_hat,
        Target.ZENITH: r_hat,
        Target.VELOCITY: v_hat,
        Target.ANTI_VELOCITY: -v_hat,
        Target.ORBIT_NORMAL: h_hat,
        Target.ANTI_ORBIT_NORMAL: -h_hat,
        Target.SUN: sun,
    }


def triad(
    primary_body: FloatArray,
    primary_inertial: FloatArray,
    secondary_body: FloatArray,
    secondary_inertial: FloatArray,
    fallback_inertial: FloatArray,
) -> FloatArray:
    """Rotation matrices body → inertial, shape (…, 3, 3).

    ``primary_*`` hold exactly; ``secondary_*`` fix the rotation about the primary. Where the
    two inertial directions are parallel (e.g. Sun at the zenith), ``fallback_inertial`` (not
    parallel to the primary) takes the place of the secondary direction.
    """
    b1 = _unit(np.broadcast_to(primary_body, primary_inertial.shape).astype(np.float64))
    b2 = _unit(np.cross(b1, np.broadcast_to(secondary_body, b1.shape)))
    b3 = np.cross(b1, b2)
    i1 = _unit(primary_inertial)
    cross = np.cross(i1, secondary_inertial)
    norm = np.linalg.norm(cross, axis=-1, keepdims=True)
    fallback = np.cross(i1, fallback_inertial)
    cross = np.where(norm > _PARALLEL, cross, fallback)
    i2 = _unit(cross)
    i3 = np.cross(i1, i2)
    body = np.stack([b1, b2, b3], axis=-1)
    inertial = np.stack([i1, i2, i3], axis=-1)
    return inertial @ np.swapaxes(body, -1, -2)


def quaternion_from_matrix(matrix: FloatArray) -> FloatArray:
    """Unit quaternion ``[w, x, y, z]`` (w ≥ 0) of rotation matrices (…, 3, 3).

    Shepperd's method: the largest of the four squared components is taken first to avoid
    dividing by a small number.
    """
    m = np.asarray(matrix, dtype=np.float64)
    trace = m[..., 0, 0] + m[..., 1, 1] + m[..., 2, 2]
    candidates = np.stack([trace, m[..., 0, 0], m[..., 1, 1], m[..., 2, 2]], axis=-1)
    choice = np.argmax(candidates, axis=-1)
    q = np.empty((*m.shape[:-2], 4), dtype=np.float64)
    for k in range(4):
        mask = choice == k
        if not np.any(mask):
            continue
        mm = m[mask]
        if k == 0:
            s = np.sqrt(1.0 + trace[mask]) * 2
            qk = np.stack(
                [
                    0.25 * s,
                    (mm[:, 2, 1] - mm[:, 1, 2]) / s,
                    (mm[:, 0, 2] - mm[:, 2, 0]) / s,
                    (mm[:, 1, 0] - mm[:, 0, 1]) / s,
                ],
                axis=-1,
            )
        elif k == 1:
            s = np.sqrt(1.0 + mm[:, 0, 0] - mm[:, 1, 1] - mm[:, 2, 2]) * 2
            qk = np.stack(
                [
                    (mm[:, 2, 1] - mm[:, 1, 2]) / s,
                    0.25 * s,
                    (mm[:, 0, 1] + mm[:, 1, 0]) / s,
                    (mm[:, 0, 2] + mm[:, 2, 0]) / s,
                ],
                axis=-1,
            )
        elif k == 2:
            s = np.sqrt(1.0 + mm[:, 1, 1] - mm[:, 0, 0] - mm[:, 2, 2]) * 2
            qk = np.stack(
                [
                    (mm[:, 0, 2] - mm[:, 2, 0]) / s,
                    (mm[:, 0, 1] + mm[:, 1, 0]) / s,
                    0.25 * s,
                    (mm[:, 1, 2] + mm[:, 2, 1]) / s,
                ],
                axis=-1,
            )
        else:
            s = np.sqrt(1.0 + mm[:, 2, 2] - mm[:, 0, 0] - mm[:, 1, 1]) * 2
            qk = np.stack(
                [
                    (mm[:, 1, 0] - mm[:, 0, 1]) / s,
                    (mm[:, 0, 2] + mm[:, 2, 0]) / s,
                    (mm[:, 1, 2] + mm[:, 2, 1]) / s,
                    0.25 * s,
                ],
                axis=-1,
            )
        q[mask] = qk
    q = q / np.linalg.norm(q, axis=-1, keepdims=True)
    return np.where(q[..., :1] < 0, -q, q)
