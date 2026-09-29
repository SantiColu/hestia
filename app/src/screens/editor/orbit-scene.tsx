import { useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";
import type { OrbitProfile } from "@/api/client";
import { FACES, type Instant, type Vec3 } from "./orbit-profile";

/**
 * 3D scene of one orbit (docs/etapas/environment.md, «Órbita 3D»). Draws the profile as the API
 * computed it; the only arithmetic is placing it in the scene (Earth radii, three.js axes).
 *
 * Units: 1 = Earth radius. Axes: the inertial frame has z to the north; three.js has y up, so
 * inertial (x, y, z) is drawn at (x, z, -y) — a rotation of -90° about x.
 */

export type CameraMode = "global" | "local";

const EARTH_RADIUS_M = 6_378_137;
const FRAME = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), -Math.PI / 2);

function world(v: Vec3 | number[] | undefined): THREE.Vector3 {
  const [x = 0, y = 0, z = 0] = v ?? [];
  return new THREE.Vector3(x / EARTH_RADIUS_M, z / EARTH_RADIUS_M, -y / EARTH_RADIUS_M);
}

function direction(v: Vec3 | number[]): THREE.Vector3 {
  const [x = 0, y = 0, z = 0] = v;
  return new THREE.Vector3(x, z, -y).normalize();
}

/** Colors of the Graphite tokens (styles.css), read once. */
function token(name: string, fallback: string): THREE.Color {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return new THREE.Color(value || fallback);
}

type Palette = Record<
  "bg" | "earth" | "grid" | "sun" | "shade" | "primary" | "cold" | "hot" | "text",
  THREE.Color
>;

function palette(): Palette {
  return {
    bg: token("--bg", "#0f1216"),
    earth: token("--surface-2", "#1d222a"),
    grid: token("--border-strong", "#38404b"),
    sun: token("--warn", "#d9a441"),
    shade: token("--idle", "#7c8594"),
    primary: token("--primary", "#5b8def"),
    cold: token("--cold", "#5aa0ee"),
    hot: token("--hot", "#ec7a48"),
    text: token("--subtle-foreground", "#667080"),
  };
}

/** Flux color: cold (0) to hot (max). */
function fluxColor(colors: Palette, value: number, max: number): THREE.Color {
  const f = max > 0 ? Math.min(Math.max(value / max, 0), 1) : 0;
  return colors.cold.clone().lerp(colors.hot, f);
}

// ---------------------------------------------------------------- pieces

function Graticule({ color }: { color: THREE.Color }) {
  const geometry = useMemo(() => {
    const points: number[] = [];
    const r = 1.001;
    const add = (a: THREE.Vector3, b: THREE.Vector3) => points.push(a.x, a.y, a.z, b.x, b.y, b.z);
    const at = (lat: number, lon: number) =>
      world([
        r * EARTH_RADIUS_M * Math.cos(lat) * Math.cos(lon),
        r * EARTH_RADIUS_M * Math.cos(lat) * Math.sin(lon),
        r * EARTH_RADIUS_M * Math.sin(lat),
      ]);
    const step = Math.PI / 36;
    for (let lat = -60; lat <= 60; lat += 30) {
      const phi = (lat * Math.PI) / 180;
      for (let lon = 0; lon < 2 * Math.PI - 1e-9; lon += step)
        add(at(phi, lon), at(phi, lon + step));
    }
    for (let lon = 0; lon < 360; lon += 30) {
      const lambda = (lon * Math.PI) / 180;
      for (let lat = -Math.PI / 2; lat < Math.PI / 2 - 1e-9; lat += step) {
        add(at(lat, lambda), at(lat + step, lambda));
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(points, 3));
    return g;
  }, []);
  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial color={color} />
    </lineSegments>
  );
}

function Earth({ rotation, colors }: { rotation: number; colors: Palette }) {
  // Rotation about the inertial z axis (three.js y).
  return (
    <group rotation={[0, rotation, 0]}>
      <mesh>
        <sphereGeometry args={[1, 64, 32]} />
        <meshBasicMaterial color={colors.earth} />
      </mesh>
      <Graticule color={colors.grid} />
    </group>
  );
}

function OrbitLine({ profile, colors }: { profile: OrbitProfile; colors: Palette }) {
  const geometry = useMemo(() => {
    const n = profile.position.length;
    const positions: number[] = [];
    const vertexColors: number[] = [];
    for (let k = 0; k < n; k++) {
      const a = world(profile.position[k]);
      const b = world(profile.position[(k + 1) % n]);
      const color = (profile.sunlit[k] ?? 1) > 0.5 ? colors.sun : colors.shade;
      positions.push(a.x, a.y, a.z, b.x, b.y, b.z);
      vertexColors.push(color.r, color.g, color.b, color.r, color.g, color.b);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    g.setAttribute("color", new THREE.Float32BufferAttribute(vertexColors, 3));
    return g;
  }, [profile, colors]);
  return (
    <lineSegments geometry={geometry}>
      <lineBasicMaterial vertexColors />
    </lineSegments>
  );
}

function Arrow({
  origin,
  dir,
  length,
  color,
}: {
  origin: THREE.Vector3;
  dir: THREE.Vector3;
  length: number;
  color: THREE.Color;
}) {
  const helper = useMemo(
    () => new THREE.ArrowHelper(dir, origin, length, color, length * 0.18, length * 0.1),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- updated below, created once
    [],
  );
  useEffect(() => {
    helper.position.copy(origin);
    helper.setDirection(dir);
    helper.setLength(length, length * 0.18, length * 0.1);
    helper.setColor(color);
  }, [helper, origin, dir, length, color]);
  return <primitive object={helper} />;
}

function ShadowCylinder({ sun, colors }: { sun: THREE.Vector3; colors: Palette }) {
  const length = 4;
  const quaternion = useMemo(
    () =>
      new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), sun.clone().negate()),
    [sun],
  );
  const position = useMemo(() => sun.clone().multiplyScalar(-length / 2), [sun]);
  return (
    <mesh quaternion={quaternion} position={position}>
      <cylinderGeometry args={[1, 1, length, 48, 1, true]} />
      <meshBasicMaterial
        color={colors.shade}
        transparent
        opacity={0.06}
        side={THREE.DoubleSide}
        depthWrite={false}
      />
    </mesh>
  );
}

/** The envelope, not to scale, with its faces colored by the total incident flux. */
function Spacecraft({
  instant,
  size,
  maxFlux,
  colors,
  onOpen,
}: {
  instant: Instant;
  size: number;
  maxFlux: number;
  colors: Palette;
  onOpen?: () => void;
}) {
  const [w, x, y, z] = instant.quaternion;
  const quaternion = FRAME.clone().multiply(new THREE.Quaternion(x, y, z, w));
  // BoxGeometry material groups are +X, -X, +Y, -Y, +Z, -Z: the order of FACES.
  const materials = FACES.map((face) =>
    fluxColor(colors, instant.faces[face]?.total ?? 0, maxFlux),
  );
  return (
    <group position={world(instant.position)} quaternion={quaternion}>
      <mesh
        onDoubleClick={(event) => {
          event.stopPropagation();
          onOpen?.();
        }}
      >
        <boxGeometry args={[size, size, size]} />
        {materials.map((color, k) => (
          <meshBasicMaterial key={FACES[k]} attach={`material-${k}`} color={color} />
        ))}
      </mesh>
      <axesHelper args={[size * 1.2]} />
    </group>
  );
}

// ---------------------------------------------------------------- cameras

function GlobalCamera({ radius }: { radius: number }) {
  const { camera, gl } = useThree();
  const view = useRef({ azimuth: 0.6, elevation: 0.35, distance: radius * 3.2 });
  useEffect(() => {
    const element = gl.domElement;
    let dragging: { x: number; y: number } | null = null;
    const down = (e: PointerEvent) => {
      dragging = { x: e.clientX, y: e.clientY };
    };
    const move = (e: PointerEvent) => {
      if (!dragging) return;
      view.current.azimuth -= (e.clientX - dragging.x) * 0.008;
      view.current.elevation = Math.max(
        -1.4,
        Math.min(1.4, view.current.elevation + (e.clientY - dragging.y) * 0.008),
      );
      dragging = { x: e.clientX, y: e.clientY };
    };
    const up = () => {
      dragging = null;
    };
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      view.current.distance = Math.max(
        1.3,
        Math.min(40, view.current.distance * (1 + e.deltaY * 0.001)),
      );
    };
    element.addEventListener("pointerdown", down);
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
    element.addEventListener("wheel", wheel, { passive: false });
    return () => {
      element.removeEventListener("pointerdown", down);
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      element.removeEventListener("wheel", wheel);
    };
  }, [gl]);
  useFrame(() => {
    const { azimuth, elevation, distance } = view.current;
    camera.up.set(0, 1, 0);
    camera.position.set(
      distance * Math.cos(elevation) * Math.sin(azimuth),
      distance * Math.sin(elevation),
      distance * Math.cos(elevation) * Math.cos(azimuth),
    );
    camera.lookAt(0, 0, 0);
  });
  return null;
}

/** Follows the satellite from behind and above, with the local vertical up (horizon visible). */
function LocalCamera({ instant }: { instant: Instant }) {
  const { camera } = useThree();
  useFrame(() => {
    const position = world(instant.position);
    const zenith = position.clone().normalize();
    const forward = direction(instant.velocity);
    const eye = position.clone().addScaledVector(zenith, 0.012).addScaledVector(forward, -0.03);
    camera.up.copy(zenith);
    camera.position.copy(eye);
    camera.lookAt(position.clone().addScaledVector(forward, 0.01));
  });
  return null;
}

// ---------------------------------------------------------------- scene

export function OrbitScene({
  profile,
  instant,
  mode,
  maxFlux,
  onOpenLocal,
}: {
  profile: OrbitProfile;
  instant: Instant;
  mode: CameraMode;
  maxFlux: number;
  onOpenLocal: () => void;
}) {
  const colors = useMemo(() => palette(), []);
  const radius = world(profile.position[0]).length();
  const sun = direction(instant.sun);
  const satellite = world(instant.position);
  const local = mode === "local";
  const size = local ? 0.004 : 0.05;
  const vector = local ? 0.012 : 0.25;

  return (
    <Canvas
      camera={{ fov: 45, near: 0.0005, far: 200, position: [0, 1, 4] }}
      className="h-full w-full"
      dpr={[1, 2]}
    >
      <color attach="background" args={[colors.bg]} />
      {local ? <LocalCamera instant={instant} /> : <GlobalCamera radius={radius} />}
      <Earth rotation={instant.earthRotation} colors={colors} />
      <OrbitLine profile={profile} colors={colors} />
      {!local && <ShadowCylinder sun={sun} colors={colors} />}
      <Arrow
        origin={local ? satellite : new THREE.Vector3()}
        dir={sun}
        length={local ? vector : radius * 1.6}
        color={colors.sun}
      />
      <Spacecraft
        instant={instant}
        size={size}
        maxFlux={maxFlux}
        colors={colors}
        onOpen={onOpenLocal}
      />
      {local && (
        <>
          <Arrow
            origin={satellite}
            dir={satellite.clone().normalize().negate()}
            length={vector}
            color={colors.shade}
          />
          <Arrow
            origin={satellite}
            dir={direction(instant.velocity)}
            length={vector}
            color={colors.primary}
          />
        </>
      )}
    </Canvas>
  );
}
