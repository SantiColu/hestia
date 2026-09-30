import type { OrbitProfile } from "@/api/client";

/**
 * Interpolation between the samples of an orbit (a result profile or the preview of a draft), to
 * animate it (docs/etapas/environment.md: «la UI dibuja `orbit_profiles` tal como llegan y solo
 * interpola entre muestras»). No physics: positions are blended linearly, attitudes with a
 * spherical blend, angles unwrapped; fluxes are the nearest sample's, so every number shown comes
 * from the API.
 */

export type Vec3 = [number, number, number];
export type Quat = [number, number, number, number];

export const FACES = ["+X", "-X", "+Y", "-Y", "+Z", "-Z"] as const;
export type FaceName = (typeof FACES)[number];

export type FaceFlux = { solar: number; albedo: number; ir: number; total: number };

/** One sampled orbit as the API gives it: a result profile (attitude and fluxes) or the preview of
 * a draft (attitude only with a complete attitude mode, never fluxes). */
export type Track = Pick<
  OrbitProfile,
  "period" | "time" | "position" | "velocity" | "sun" | "sunlit" | "earth_rotation_angle"
> & {
  quaternion: number[][] | null;
  faces?: OrbitProfile["faces"];
};

export type Instant = {
  /** s from the profile's epoch, in [0, period). */
  time: number;
  position: Vec3;
  velocity: Vec3;
  sun: Vec3;
  sunlit: number;
  /** Body → inertial, [w, x, y, z]; null without an attitude. */
  quaternion: Quat | null;
  earthRotation: number;
  /** Incident fluxes at their maximum design values at the nearest sample, W/m² (as the API
   * computed them, never interpolated); null without fluxes. */
  faces: Record<FaceName, FaceFlux> | null;
};

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

/** A point between two samples of an orbit along the arc they span: the direction is blended on
 * the sphere and the length linearly, so points of a circular orbit stay on it (a straight blend
 * would cut the chord). */
export function arc(a: number[], b: number[], f: number): Vec3 {
  const la = Math.hypot(...a);
  const lb = Math.hypot(...b);
  if (la === 0 || lb === 0) return lerp3(a, b, f);
  const ua = a.map((v) => v / la);
  const ub = b.map((v) => v / lb);
  const dot = Math.min(
    1,
    Math.max(
      -1,
      ua.reduce((sum, v, i) => sum + v * at(ub, i), 0),
    ),
  );
  const theta = Math.acos(dot);
  const length = lerp(la, lb, f);
  if (theta < 1e-9) return lerp3(ua, ub, f).map((v) => v * length) as Vec3;
  const wa = Math.sin((1 - f) * theta) / Math.sin(theta);
  const wb = Math.sin(f * theta) / Math.sin(theta);
  return ua.map((v, i) => (wa * v + wb * at(ub, i)) * length) as Vec3;
}

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

function facesAt(track: Track, k: number): Record<FaceName, FaceFlux> | null {
  if (!track.faces) return null;
  const faces = {} as Record<FaceName, FaceFlux>;
  for (const face of track.faces) {
    faces[face.face as FaceName] = {
      solar: at(face.solar_max, k),
      albedo: at(face.albedo_max, k),
      ir: at(face.ir_max, k),
      total: at(face.total_max, k),
    };
  }
  return faces;
}

export function instantAt(track: Track, time: number): Instant {
  const n = track.time.length;
  const period = track.period;
  const t = ((time % period) + period) % period;
  const step = period / n;
  const i = Math.min(Math.floor(t / step), n - 1);
  const j = (i + 1) % n;
  const f = (t - i * step) / step;
  const { quaternion } = track;
  return {
    time: t,
    position: arc(at(track.position, i), at(track.position, j), f),
    velocity: arc(at(track.velocity, i), at(track.velocity, j), f),
    sun: lerp3(at(track.sun, i), at(track.sun, j), f),
    sunlit: lerp(at(track.sunlit, i), at(track.sunlit, j), f),
    quaternion: quaternion ? slerp(at(quaternion, i), at(quaternion, j), f) : null,
    earthRotation: angle(at(track.earth_rotation_angle, i), at(track.earth_rotation_angle, j), f),
    faces: facesAt(track, f < 0.5 ? i : j),
  };
}

/** Largest total incident flux on any face along the profile (top of the color scale). */
export function maxTotalFlux(profile: OrbitProfile): number {
  return Math.max(0, ...profile.faces.flatMap((face) => face.total_max));
}
