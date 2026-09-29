import type { OrbitProfile } from "@/api/client";

/**
 * Interpolation between the samples of an orbit profile, to animate it (docs/etapas/environment.md:
 * «la UI dibuja `orbit_profiles` tal como llegan y solo interpola entre muestras»). No physics:
 * positions are blended linearly, attitudes with a spherical blend, angles unwrapped; fluxes are
 * the nearest sample's, so every number shown comes from the API.
 */

export type Vec3 = [number, number, number];
export type Quat = [number, number, number, number];

export const FACES = ["+X", "-X", "+Y", "-Y", "+Z", "-Z"] as const;
export type FaceName = (typeof FACES)[number];

export type FaceFlux = { solar: number; albedo: number; ir: number; total: number };

export type Instant = {
  /** s from the profile's epoch, in [0, period). */
  time: number;
  position: Vec3;
  velocity: Vec3;
  sun: Vec3;
  sunlit: number;
  /** Body → inertial, [w, x, y, z]. */
  quaternion: Quat;
  earthRotation: number;
  /** Incident fluxes at their maximum design values at the nearest sample, W/m² (as the API
   * computed them, never interpolated). */
  faces: Record<FaceName, FaceFlux>;
};

/** Period of the profile (from the API): the samples cover it uniformly. */
export function profilePeriod(profile: OrbitProfile): number {
  return profile.period;
}

/** Element k of a list the API guarantees to have (every profile list has one per sample). */
function at<T>(list: T[], k: number): T {
  return list[k] as T;
}

const lerp = (a: number, b: number, f: number) => a + (b - a) * f;
const lerp3 = (a: number[], b: number[], f: number): Vec3 => [
  lerp(at(a, 0), at(b, 0), f),
  lerp(at(a, 1), at(b, 1), f),
  lerp(at(a, 2), at(b, 2), f),
];

function slerp(a: number[], b: number[], f: number): Quat {
  let dot = a.reduce((sum, v, i) => sum + v * at(b, i), 0);
  const sign = dot < 0 ? -1 : 1;
  dot *= sign;
  if (dot > 0.9995) {
    const q = a.map((v, i) => lerp(v, sign * at(b, i), f));
    const norm = Math.hypot(...q);
    return q.map((v) => v / norm) as Quat;
  }
  const theta = Math.acos(dot);
  const wa = Math.sin((1 - f) * theta) / Math.sin(theta);
  const wb = (sign * Math.sin(f * theta)) / Math.sin(theta);
  return a.map((v, i) => wa * v + wb * at(b, i)) as Quat;
}

function angle(a: number, b: number, f: number): number {
  let delta = b - a;
  if (delta > Math.PI) delta -= 2 * Math.PI;
  if (delta < -Math.PI) delta += 2 * Math.PI;
  return a + delta * f;
}

export function instantAt(profile: OrbitProfile, time: number): Instant {
  const n = profile.time.length;
  const period = profilePeriod(profile);
  const t = ((time % period) + period) % period;
  const step = period / n;
  const i = Math.min(Math.floor(t / step), n - 1);
  const j = (i + 1) % n;
  const f = (t - i * step) / step;
  const nearest = f < 0.5 ? i : j;
  const faces = {} as Record<FaceName, FaceFlux>;
  for (const face of profile.faces) {
    faces[face.face as FaceName] = {
      solar: at(face.solar_max, nearest),
      albedo: at(face.albedo_max, nearest),
      ir: at(face.ir_max, nearest),
      total: at(face.total_max, nearest),
    };
  }
  return {
    time: t,
    position: lerp3(at(profile.position, i), at(profile.position, j), f),
    velocity: lerp3(at(profile.velocity, i), at(profile.velocity, j), f),
    sun: lerp3(at(profile.sun, i), at(profile.sun, j), f),
    sunlit: lerp(at(profile.sunlit, i), at(profile.sunlit, j), f),
    quaternion: slerp(at(profile.quaternion, i), at(profile.quaternion, j), f),
    earthRotation: angle(
      at(profile.earth_rotation_angle, i),
      at(profile.earth_rotation_angle, j),
      f,
    ),
    faces,
  };
}

/** Largest total incident flux on any face along the profile (top of the color scale). */
export function maxTotalFlux(profile: OrbitProfile): number {
  return Math.max(0, ...profile.faces.flatMap((face) => face.total_max));
}
