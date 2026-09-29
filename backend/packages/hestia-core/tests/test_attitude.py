"""Body frame from axis → direction pairs (TRIAD) and quaternions."""

import math

import numpy as np
import pytest

from hestia_core.attitude import AXIS_VECTORS, quaternion_from_matrix, target_directions, triad
from hestia_core.mission import Axis, Target


def _rotate(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    """v' = q v q* for q = [w, x, y, z] (Hamilton)."""
    w, xyz = q[0], q[1:]
    return v + 2 * np.cross(xyz, np.cross(xyz, v) + w * v)


def test_primary_holds_exactly_and_secondary_sets_the_roll() -> None:
    rng = np.random.default_rng(7)
    t1 = rng.normal(size=(50, 3))
    t2 = rng.normal(size=(50, 3))
    fallback = np.tile([0.0, 0.0, 1.0], (50, 1))
    a1, a2 = np.array(AXIS_VECTORS[Axis.PZ]), np.array(AXIS_VECTORS[Axis.PX])
    matrix = triad(a1, t1, a2, t2, fallback)
    t1_hat = t1 / np.linalg.norm(t1, axis=-1, keepdims=True)
    assert np.allclose(matrix @ a1, t1_hat, atol=1e-12)
    # Proper rotations.
    assert np.allclose(matrix @ np.swapaxes(matrix, -1, -2), np.eye(3), atol=1e-12)
    assert np.allclose(np.linalg.det(matrix), 1.0, atol=1e-12)
    # The secondary axis lies in the plane of both directions, on the side of t2.
    secondary = matrix @ a2
    assert np.allclose(np.sum(secondary * np.cross(t1, t2), axis=-1), 0.0, atol=1e-12)
    along_t2 = np.sum(secondary * (t2 - np.sum(t2 * t1_hat, -1, keepdims=True) * t1_hat), -1)
    assert np.all(along_t2 > 0)


def test_parallel_directions_use_the_fallback() -> None:
    t = np.array([[1.0, 0.0, 0.0]])
    matrix = triad(
        np.array(AXIS_VECTORS[Axis.PZ]),
        t,
        np.array(AXIS_VECTORS[Axis.PX]),
        -t,
        np.array([[0.0, 1.0, 0.0]]),
    )
    assert np.all(np.isfinite(matrix))
    assert np.allclose(matrix[0] @ np.array([0.0, 0.0, 1.0]), [1.0, 0.0, 0.0])


def test_quaternion_of_a_quarter_turn_about_z() -> None:
    # Hand calculation: 90° about +z is q = [cos 45°, 0, 0, sin 45°]; it takes +x to +y.
    c = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    q = quaternion_from_matrix(c)
    assert np.allclose(q, [math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5)], atol=1e-12)


def test_quaternions_rotate_like_their_matrices() -> None:
    rng = np.random.default_rng(3)
    matrix = triad(
        np.array(AXIS_VECTORS[Axis.MY]),
        rng.normal(size=(200, 3)),
        np.array(AXIS_VECTORS[Axis.PZ]),
        rng.normal(size=(200, 3)),
        np.tile([1.0, 0.0, 0.0], (200, 1)),
    )
    q = quaternion_from_matrix(matrix)
    assert np.allclose(np.linalg.norm(q, axis=-1), 1.0)
    assert np.all(q[:, 0] >= 0)
    v = rng.normal(size=3)
    for k in range(200):
        assert np.allclose(_rotate(q[k], v), matrix[k] @ v, atol=1e-10)


def test_target_directions_on_a_circular_orbit() -> None:
    position = np.array([[7e6, 0.0, 0.0]])
    velocity = np.array([[0.0, 7.5e3, 0.0]])
    directions = target_directions(position, velocity, np.array([0.0, 0.0, 2.0]))
    assert np.allclose(directions[Target.NADIR], [[-1.0, 0.0, 0.0]])
    assert np.allclose(directions[Target.VELOCITY], [[0.0, 1.0, 0.0]])
    assert np.allclose(directions[Target.ORBIT_NORMAL], [[0.0, 0.0, 1.0]])
    assert np.allclose(directions[Target.SUN], [[0.0, 0.0, 1.0]])
    assert directions[Target.ZENITH] == pytest.approx(-directions[Target.NADIR])
